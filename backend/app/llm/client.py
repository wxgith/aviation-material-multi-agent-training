import json
import re
from time import perf_counter
from copy import deepcopy
from typing import Any

import httpx

from app.core.config import settings
from app.llm.prompts import (
    guided_inquiry_prompt,
    guided_review_prompt,
    resource_generation_prompt,
)


SYSTEM_PROMPT = (
    "你是严谨的航空工程材料损伤分析训练助手。"
    "必须遵守知识证据边界，将观察、推断和决策建议明确分层。"
)
RESOURCE_PROMPT_VERSION = "resource-generation-v2"
INQUIRY_PROMPT_VERSION = "guided-inquiry-v2"
REVIEW_PROMPT_VERSION = "guided-review-v2"


class LLMClient:
    def enabled(self) -> bool:
        return bool(settings.llm_enabled)

    def connected_configured(self) -> bool:
        return bool(settings.llm_enabled and settings.llm_base_url and settings.llm_model)

    def chat(
        self,
        prompt: str,
        system_prompt: str = SYSTEM_PROMPT,
        *,
        json_mode: bool = False,
    ) -> str:
        if not self.connected_configured():
            raise RuntimeError("LLM 已启用，但 LLM_BASE_URL 或 LLM_MODEL 未配置。")

        url = _chat_completions_url(settings.llm_base_url or "")
        headers = {"Content-Type": "application/json"}
        if settings.llm_api_key:
            headers["Authorization"] = f"Bearer {settings.llm_api_key}"
        payload = {
            "model": settings.llm_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        else:
            payload["max_tokens"] = settings.llm_max_tokens
        with httpx.Client(timeout=settings.llm_timeout) as client:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ValueError("LLM 返回结构中缺少 choices[0].message.content。") from exc

    def chat_json(self, prompt: str, system_prompt: str = SYSTEM_PROMPT) -> dict[str, Any]:
        last_error: Exception | None = None
        attempts = max(1, settings.llm_retries + 1)
        for attempt in range(attempts):
            try:
                suffix = "" if attempt == 0 else "\n上次输出无法解析。请只返回合法 JSON 对象。"
                json_prompt = prompt + suffix + "\n请仅输出合法 JSON 对象。"
                parsed = _extract_json(
                    self.chat(json_prompt, system_prompt=system_prompt, json_mode=True)
                )
                if not isinstance(parsed, dict):
                    raise ValueError("LLM 响应不是 JSON 对象。")
                return parsed
            except Exception as exc:
                last_error = exc
        raise RuntimeError(f"LLM 结构化输出失败：{last_error}") from last_error


llm_client = LLMClient()


def maybe_generate_resources_with_llm(
    profile: dict,
    domain: str,
    diagnosis: Any,
    retrieved_chunks: list[dict],
    learning_goal: str,
    base_resources: dict,
) -> dict:
    resources = deepcopy(base_resources)
    audit = _new_audit(RESOURCE_PROMPT_VERSION)
    if not settings.llm_enabled or not settings.llm_resource_generation_enabled:
        resources["generation_mode"] = (
            "mock-template" if not settings.llm_enabled else "mock-template-stable"
        )
        if settings.llm_enabled:
            audit["outcome"] = "disabled"
            audit["fallback_reason"] = (
                "LLM 整包资源生成已关闭；使用稳定模板，智能问答仍可调用 LLM。"
            )
        resources["generation_audit"] = audit
        return resources

    started = perf_counter()
    try:
        prompt = resource_generation_prompt(
            profile=profile,
            domain=domain,
            diagnosis=diagnosis.model_dump() if hasattr(diagnosis, "model_dump") else diagnosis,
            retrieved_chunks=retrieved_chunks,
            learning_goal=learning_goal,
            base_resources=resources,
        )
        parsed = llm_client.chat_json(prompt)
        _validate_generated_resources(parsed, retrieved_chunks)
        parsed["personalization"] = resources.get("personalization", {})
        parsed["evidence_boundary"] = resources.get("evidence_boundary", {})
        parsed["generation_mode"] = "llm"
        parsed["generation_audit"] = _finish_audit(audit, started, "success")
        return parsed
    except Exception as exc:
        resources["generation_mode"] = "mock-template-fallback"
        resources["llm_error"] = _safe_error(exc)
        resources["generation_audit"] = _finish_audit(
            audit, started, "fallback", resources["llm_error"]
        )
        return resources


def maybe_generate_guided_answer_with_llm(
    *,
    profile: dict,
    domain: str,
    diagnosis: Any,
    learning_goal: str,
    question: str,
    retrieved_chunks: list[dict],
    history: list[dict],
    page_context: dict | None = None,
) -> tuple[dict[str, Any] | None, str, dict[str, Any]]:
    audit = _new_audit(INQUIRY_PROMPT_VERSION)
    if not settings.llm_enabled:
        return None, "mock-template", audit
    started = perf_counter()
    try:
        prompt = guided_inquiry_prompt(
            profile=profile,
            domain=domain,
            diagnosis=diagnosis.model_dump() if hasattr(diagnosis, "model_dump") else diagnosis,
            learning_goal=learning_goal,
            question=question,
            retrieved_chunks=retrieved_chunks,
            history=history,
            page_context=page_context,
        )
        return (
            llm_client.chat_json(prompt),
            "llm",
            _finish_audit(audit, started, "success"),
        )
    except Exception as exc:
        error = _safe_error(exc)
        return (
            {"llm_error": error},
            "mock-template-fallback",
            _finish_audit(audit, started, "fallback", error),
        )


def maybe_review_guided_answer_with_llm(
    question: str,
    answer: dict,
    retrieved_chunks: list[dict],
) -> tuple[dict[str, Any] | None, str, dict[str, Any]]:
    audit = _new_audit(REVIEW_PROMPT_VERSION)
    if not settings.llm_enabled or not settings.llm_semantic_review_enabled:
        if settings.llm_enabled:
            audit["outcome"] = "disabled"
            audit["fallback_reason"] = (
                "LLM 语义复核已关闭；使用确定性证据闭合与边界规则审核。"
            )
        return None, "rule-review", audit
    started = perf_counter()
    try:
        prompt = guided_review_prompt(question, answer, retrieved_chunks)
        parsed = llm_client.chat_json(
            prompt,
            system_prompt="你是独立的航空工程材料专业审核纠偏 Agent，只依据给定证据审核。",
        )
        return (
            parsed,
            "llm-assisted-review",
            _finish_audit(audit, started, "success"),
        )
    except Exception as exc:
        error = _safe_error(exc)
        return (
            {"review_error": error},
            "rule-review-fallback",
            _finish_audit(audit, started, "fallback", error),
        )


def _chat_completions_url(base_url: str) -> str:
    normalized = base_url.rstrip("/")
    if normalized.endswith("/chat/completions"):
        return normalized
    return normalized + "/chat/completions"


def _validate_generated_resources(resources: dict, retrieved_chunks: list[dict]) -> None:
    required_types = {
        "personalized_lecture": dict,
        "practical_guide": dict,
        "graded_quiz": list,
        "case_task": dict,
        "difficulty_match": dict,
    }
    for key, expected_type in required_types.items():
        if not isinstance(resources.get(key), expected_type):
            raise ValueError(f"LLM 资源字段 {key} 缺失或类型不正确。")

    sections = resources["personalized_lecture"].get("sections")
    if not isinstance(sections, list) or not sections:
        raise ValueError("LLM 讲义缺少 sections。")
    if not resources["practical_guide"].get("constraints"):
        raise ValueError("LLM 实操指南缺少 constraints。")
    if len(resources["graded_quiz"]) < 3:
        raise ValueError("LLM 分阶测试题数量不足。")
    if any(not item.get("explanation") for item in resources["graded_quiz"]):
        raise ValueError("LLM 分阶测试题缺少解析。")

    allowed_ids = {chunk.get("id") for chunk in retrieved_chunks}
    cited_ids = {
        evidence_id
        for section in sections
        for evidence_id in section.get("evidence_ids", [])
    }
    cited_ids.update(resources["practical_guide"].get("evidence_ids", []))
    cited_ids.update(resources["case_task"].get("evidence_ids", []))
    invalid_ids = cited_ids - allowed_ids
    if invalid_ids:
        raise ValueError(f"LLM 引用了未检索证据：{', '.join(sorted(invalid_ids))}")
    if allowed_ids and not cited_ids:
        raise ValueError("LLM 资源未绑定 evidence_ids。")

    _validate_resource_claim_boundaries(resources, retrieved_chunks)


def _validate_resource_claim_boundaries(
    resources: dict, retrieved_chunks: list[dict]
) -> None:
    chunks_by_id = {
        str(chunk.get("id", "")): chunk
        for chunk in retrieved_chunks
        if chunk.get("id")
    }
    text_blocks: list[tuple[str, str, list[str]]] = []
    for section in resources.get("personalized_lecture", {}).get("sections", []):
        text_blocks.append(
            (
                f"讲义章节“{section.get('heading', '')}”",
                str(section.get("content", "")),
                [str(item) for item in section.get("evidence_ids", [])],
            )
        )
    guide = resources.get("practical_guide", {})
    guide_text = " ".join(
        str(item)
        for item in guide.get("steps", []) + guide.get("constraints", [])
    )
    text_blocks.append(
        ("实操指南", guide_text, [str(item) for item in guide.get("evidence_ids", [])])
    )
    case = resources.get("case_task", {})
    text_blocks.append(
        (
            "案例任务",
            str(case.get("brief", "")),
            [str(item) for item in case.get("evidence_ids", [])],
        )
    )

    for label, text, evidence_ids in text_blocks:
        if not text.strip():
            continue
        compact = re.sub(r"\s+", "", text)
        if re.search(r"(?:未|没有)(?:显式)?(?:列出|记录|提供).{0,18}(?:但)?(?:隐含|可推定|默认存在)", compact):
            raise ValueError(f"{label}把未记录工况描述为隐含或可推定条件。")
        evidence_text = " ".join(
            str(chunks_by_id[evidence_id].get("content", ""))
            for evidence_id in evidence_ids
            if evidence_id in chunks_by_id
        )
        if _has_unqualified_causal_claim(text, evidence_text):
            raise ValueError(f"{label}包含未标注为待验证假设的确定性因果表述。")

        unsupported_values = sorted(
            value
            for value in _measurement_tokens(text)
            if value not in _measurement_tokens(evidence_text)
        )
        if unsupported_values:
            raise ValueError(
                f"{label}包含绑定证据未记录的数值：{', '.join(unsupported_values)}。"
            )


def _measurement_tokens(text: str) -> set[str]:
    normalized = (
        str(text)
        .lower()
        .replace("摄氏度", "°c")
        .replace("℃", "°c")
        .replace("天", "d")
        .replace("小时", "h")
        .replace("米", "m")
    )
    pattern = r"(?<![\w.])\d+(?:\.\d+)?\s*(?:mpa|°c|mg|ha|hz|mm|n|m|d|h|%)\b"
    tokens = {re.sub(r"\s+", "", item) for item in re.findall(pattern, normalized)}
    tokens.update(_markdown_table_measurement_tokens(normalized))
    return tokens


def _markdown_table_measurement_tokens(text: str) -> set[str]:
    """Recover units carried by Markdown table headers, such as `aging/d | 7`."""
    cells = [cell.strip() for cell in str(text).split("|") if cell.strip()]
    separator = re.compile(r"^:?-{3,}:?$")
    unit_suffix = re.compile(
        r"(?:/|\[|\()\s*(mpa|°c|mg|ha|hz|mm|n|m|d|h|%)\s*(?:\]|\))?$"
    )
    numeric = re.compile(r"^[+-]?\d+(?:\.\d+)?$")
    tokens: set[str] = set()
    index = 0
    while index < len(cells):
        if not separator.fullmatch(cells[index]):
            index += 1
            continue
        separator_end = index
        while separator_end < len(cells) and separator.fullmatch(cells[separator_end]):
            separator_end += 1
        width = separator_end - index
        if width < 2 or index < width:
            index = separator_end
            continue
        headers = cells[index - width:index]
        units = []
        for header in headers:
            match = unit_suffix.search(header)
            units.append(match.group(1) if match else "")
        row_start = separator_end
        while row_start + width <= len(cells):
            row = cells[row_start:row_start + width]
            if sum(bool(numeric.fullmatch(value)) for value in row) < 2:
                break
            for value, unit in zip(row, units):
                if unit and numeric.fullmatch(value):
                    tokens.add(f"{value}{unit}")
            row_start += width
        index = max(separator_end, row_start)
    return tokens


def _has_unqualified_causal_claim(text: str, evidence_text: str) -> bool:
    consequence_terms = (
        "磨耗率", "脆性", "剥落", "裂纹", "交联", "硬化", "软化", "摩擦系数",
        "质量损失", "分层", "纤维断裂", "氧化膜", "热衰退", "失效",
    )
    for sentence in re.split(r"[。！？;；\n]", text):
        if not re.search(r"(?:导致|因此|进而|从而).*(?:增加|降低|改变|影响|萌生|剥落|失效)", sentence):
            continue
        if not re.search(r"(?:可能|假设|推断|待验证|提示|可解释为|证据支持)", sentence):
            consequence = re.split(r"(?:导致|因此|进而|从而)", sentence, maxsplit=1)[-1]
            terms = [term for term in consequence_terms if term in consequence]
            if terms and not all(term in evidence_text for term in terms):
                return True
    return False


def _extract_json(content: str) -> Any:
    content = content.strip()
    if content.startswith("```"):
        lines = content.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        content = "\n".join(lines).strip()
    start = content.find("{")
    end = content.rfind("}")
    if start >= 0 and end >= start:
        content = content[start:end + 1]
    return json.loads(content)


def _safe_error(exc: Exception) -> str:
    message = str(exc).replace(str(settings.llm_api_key or "__no_key__"), "***")
    return message[:500]


def _new_audit(prompt_version: str) -> dict[str, Any]:
    return {
        "prompt_version": prompt_version,
        "model": settings.llm_model or "mock-template",
        "provider_configured": bool(settings.llm_base_url and settings.llm_model),
        "latency_ms": 0,
        "outcome": "disabled" if not settings.llm_enabled else "pending",
        "fallback_reason": "",
    }


def _finish_audit(
    audit: dict[str, Any],
    started: float,
    outcome: str,
    fallback_reason: str = "",
) -> dict[str, Any]:
    return {
        **audit,
        "latency_ms": round((perf_counter() - started) * 1000),
        "outcome": outcome,
        "fallback_reason": fallback_reason,
    }
