from app.core.config import settings
from app.llm import client as client_module
from app.llm.client import LLMClient, maybe_review_guided_answer_with_llm


def test_chat_json_uses_json_object_mode_without_output_token_cap(monkeypatch):
    captured: dict = {}

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {"choices": [{"message": {"content": '{"ok": true}'}}]}

    class FakeHttpClient:
        def __init__(self, **kwargs) -> None:
            captured["client_kwargs"] = kwargs

        def __enter__(self):
            return self

        def __exit__(self, *args) -> None:
            return None

        def post(self, url: str, *, headers: dict, json: dict):
            captured["url"] = url
            captured["headers"] = headers
            captured["payload"] = json
            return FakeResponse()

    monkeypatch.setattr(settings, "llm_enabled", True)
    monkeypatch.setattr(settings, "llm_base_url", "https://example.test/v1")
    monkeypatch.setattr(settings, "llm_api_key", "test-key")
    monkeypatch.setattr(settings, "llm_model", "qwen-plus")
    monkeypatch.setattr(settings, "llm_retries", 0)
    monkeypatch.setattr(client_module.httpx, "Client", FakeHttpClient)

    result = LLMClient().chat_json("请输出 JSON")

    assert result == {"ok": True}
    assert captured["payload"]["response_format"] == {"type": "json_object"}
    assert "max_tokens" not in captured["payload"]
    assert "JSON" in captured["payload"]["messages"][1]["content"]


def test_stable_mode_uses_rule_review_without_second_llm_call(monkeypatch):
    monkeypatch.setattr(settings, "llm_enabled", True)
    monkeypatch.setattr(settings, "llm_semantic_review_enabled", False)
    monkeypatch.setattr(
        client_module.llm_client,
        "chat_json",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("stable review mode must not call the LLM")
        ),
    )

    review, mode, audit = maybe_review_guided_answer_with_llm(
        "为什么不能只看形貌？",
        {"answer": "需要结合工况。", "evidence_ids": ["e-1"]},
        [{"id": "e-1", "content": "需记录载荷与温度。"}],
    )

    assert review is None
    assert mode == "rule-review"
    assert audit["outcome"] == "disabled"
