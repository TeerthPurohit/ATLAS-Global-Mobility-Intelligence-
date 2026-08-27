import sys
from pathlib import Path
from unittest.mock import MagicMock

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "rag"))

import llm_client  # noqa: E402


def _fake_openai_client(response_text: str = "ok", raise_exc: Exception | None = None):
    client = MagicMock()
    if raise_exc:
        client.chat.completions.create.side_effect = raise_exc
    else:
        resp = MagicMock()
        resp.choices[0].message.content = response_text
        client.chat.completions.create.return_value = resp
    return client


def test_local_model_tried_first_when_configured(monkeypatch):
    monkeypatch.setattr(llm_client, "LOCAL_MODEL_BASE_URL", "http://vm:8080/v1")
    monkeypatch.setattr(llm_client, "LOCAL_MODEL_API_KEY", "test-key")
    monkeypatch.setattr(llm_client, "DEEPSEEK_API_KEY", "")

    local_client = _fake_openai_client("local response")
    calls = []

    def fake_openai_ctor(*, api_key=None, base_url=None):
        calls.append((api_key, base_url))
        return local_client

    monkeypatch.setattr(llm_client, "OpenAI", fake_openai_ctor)
    resp = llm_client.chat_completion(model="gpt-5.4-nano", messages=[{"role": "user", "content": "hi"}])

    assert resp.choices[0].message.content == "local response"
    assert calls[0] == ("test-key", "http://vm:8080/v1")


def test_falls_through_to_deepseek_when_local_fails(monkeypatch):
    monkeypatch.setattr(llm_client, "LOCAL_MODEL_BASE_URL", "http://vm:8080/v1")
    monkeypatch.setattr(llm_client, "LOCAL_MODEL_API_KEY", "test-key")
    monkeypatch.setattr(llm_client, "DEEPSEEK_API_KEY", "ds-key")

    local_client = _fake_openai_client(raise_exc=ConnectionError("vm down"))
    deepseek_client = _fake_openai_client("deepseek response")
    ctors = iter([local_client, deepseek_client])
    monkeypatch.setattr(llm_client, "OpenAI", lambda **kwargs: next(ctors))

    resp = llm_client.chat_completion(model="gpt-5.4-nano", messages=[{"role": "user", "content": "hi"}])
    assert resp.choices[0].message.content == "deepseek response"


def test_no_local_model_configured_skips_straight_to_deepseek(monkeypatch):
    monkeypatch.setattr(llm_client, "LOCAL_MODEL_BASE_URL", "")
    monkeypatch.setattr(llm_client, "DEEPSEEK_API_KEY", "ds-key")

    deepseek_client = _fake_openai_client("deepseek response")
    monkeypatch.setattr(llm_client, "OpenAI", lambda **kwargs: deepseek_client)

    resp = llm_client.chat_completion(model="gpt-5.4-nano", messages=[{"role": "user", "content": "hi"}])
    assert resp.choices[0].message.content == "deepseek response"
