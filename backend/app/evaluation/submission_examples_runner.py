"""Generate complete, reproducible learner input/output examples through the live API."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "evaluation" / "submission_examples"

CASES = [
    {
        "profile_id": "undergrad_basic",
        "domain": "tire",
        "correct_count": 3,
        "learning_goal": "理解航空轮胎热氧老化与滑动磨损损伤机理，并能完成基本损伤判读。",
    },
    {
        "profile_id": "grad_materials",
        "domain": "brake",
        "correct_count": 4,
        "learning_goal": "分析航空刹车片高温摩擦、热衰退与磨损形貌证据链，并设计变量控制方案。",
    },
    {
        "profile_id": "maintenance_new",
        "domain": "composite",
        "correct_count": 3,
        "learning_goal": "识别复合材料板冲击损伤、分层风险和无损检测图像，形成规范复检建议。",
    },
]


def _request_json(url: str, payload: dict[str, Any] | None = None) -> Any:
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST" if payload is not None else "GET",
    )
    with urlopen(request, timeout=120) as response:
        return json.loads(response.read().decode("utf-8"))


def _wrong_answer(question: dict[str, Any]) -> str:
    return next(option for option in question["options"] if option != question["answer"])


def generate_examples(api_base: str, output_dir: Path) -> list[dict[str, Any]]:
    profiles = {
        item["profile_id"]: item for item in _request_json(f"{api_base}/profiles")
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    summaries: list[dict[str, Any]] = []

    for case in CASES:
        profile = profiles[case["profile_id"]]
        questions = _request_json(f"{api_base}/questions?domain={case['domain']}")
        answers = [
            {
                "question_id": question["id"],
                "answer": question["answer"] if index < case["correct_count"] else _wrong_answer(question),
            }
            for index, question in enumerate(questions)
        ]
        diagnosis_submission = {
            "profile_id": case["profile_id"],
            "domain": case["domain"],
            "answers": answers,
        }
        diagnosis_result = _request_json(f"{api_base}/diagnosis", diagnosis_submission)
        agent_submission = {
            "profile_id": case["profile_id"],
            "domain": case["domain"],
            "diagnosis_result": diagnosis_result,
            "learning_goal": case["learning_goal"],
        }
        agent_run = _request_json(f"{api_base}/agent/run", agent_submission)
        session_id = agent_run["session_id"]
        resources = _request_json(f"{api_base}/sessions/{session_id}/resources")
        report = _request_json(f"{api_base}/sessions/{session_id}/report")

        example = {
            "example_purpose": "比赛方案要求的差异化学习者完整输入、中间过程与生成结果样例",
            "runtime_mode": _request_json(f"{api_base}/health"),
            "profile_input": profile,
            "training_domain": case["domain"],
            "learning_goal": case["learning_goal"],
            "diagnosis_submission": diagnosis_submission,
            "diagnosis_result": diagnosis_result,
            "agent_run": agent_run,
            "generated_resources": resources,
            "learning_report": report,
        }
        file_name = f"{case['profile_id']}_{case['domain']}_complete_example.json"
        (output_dir / file_name).write_text(
            json.dumps(example, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        summaries.append(
            {
                "file": file_name,
                "learner": profile["name"],
                "domain": case["domain"],
                "score": diagnosis_result["score"],
                "agent_steps": len(agent_run["agent_steps"]),
                "resource_types": 4,
                "knowledge_source": next(
                    (
                        step.get("details", {}).get("knowledge_source")
                        for step in agent_run["agent_steps"]
                        if step["agent_name"] == "专业知识检索 Agent"
                    ),
                    "unknown",
                ),
            }
        )

    return summaries


def write_summary(output_dir: Path, summaries: list[dict[str, Any]]) -> None:
    rows = [
        "# 差异化学习者完整输入输出样例",
        "",
        "本目录由 `python -m app.evaluation.submission_examples_runner` 通过当前运行中的后端 API 自动生成。",
        "每个 JSON 均包含学习者画像、诊断提交、诊断结果、6 个 Agent 中间步骤、4 类生成资源和学情报告。",
        "",
        "| 学习者 | 领域 | 得分 | Agent 步骤 | 资源形态 | 检索来源 | 文件 |",
        "| --- | --- | ---: | ---: | ---: | --- | --- |",
    ]
    rows.extend(
        f"| {item['learner']} | {item['domain']} | {item['score']} | {item['agent_steps']} | "
        f"{item['resource_types']} | {item['knowledge_source']} | `{item['file']}` |"
        for item in summaries
    )
    rows.extend(
        [
            "",
            "> 这些文件是演示和提交测试数据，不代表专业指标已由专家签字确认。",
        ]
    )
    (output_dir / "README.md").write_text("\n".join(rows) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-base", default="http://127.0.0.1:8000/api")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    try:
        summaries = generate_examples(args.api_base.rstrip("/"), args.output_dir)
    except URLError as exc:
        raise SystemExit(f"后端 API 不可用：{exc}") from exc
    write_summary(args.output_dir, summaries)
    print(json.dumps({"generated": len(summaries), "output_dir": str(args.output_dir)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
