import json

import pytest


@pytest.mark.asyncio
async def test_live_reporter_uses_agent_explanations_and_evidence(monkeypatch):
    from app.agents import workers

    captured = {}

    async def fake_complete_json(system, user, max_tokens):
        captured["system"] = system
        captured["context"] = json.loads(user)
        captured["max_tokens"] = max_tokens
        return {
            "result": "Detailed findings.",
            "explanation": "Compared the available research and verification outputs.",
            "evidence": ["Source supplied by the research agent."],
            "uncertainty": "medium",
            "limitations": "No live browsing was available.",
        }

    monkeypatch.setattr(workers, "is_live", lambda: True)
    monkeypatch.setattr(workers, "complete_json", fake_complete_json)

    report = await workers.run_reporter(
        [{
            "agent": "research",
            "result": "Research summary.",
            "explanation": "Reasoning summary.",
            "evidence": ["Source supplied by the research agent."],
            "uncertainty": "medium",
            "limitations": "Source coverage is limited.",
        }],
        "Compare three products.",
    )

    assert captured["context"]["goal"] == "Compare three products."
    assert captured["context"]["prior_agent_outputs"][0]["explanation"] == "Reasoning summary."
    assert captured["context"]["prior_agent_outputs"][0]["evidence"] == [
        "Source supplied by the research agent."
    ]
    assert "Do not invent facts" in captured["system"]
    assert "No live web search or browsing tool is configured" in captured["context"]["available_tools"]
    assert captured["context"]["provider"] in {"openai", "anthropic"}
    assert captured["context"]["model"]
    assert captured["max_tokens"] == 2800
    assert report["result"] == "Detailed findings."


@pytest.mark.asyncio
async def test_openai_client_sends_json_mode_and_parses_response(monkeypatch):
    from app.agents import llm_client

    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"choices": [{"message": {"content": '{"result":"Answer"}'}}]}

    class FakeAsyncClient:
        def __init__(self, timeout):
            captured["timeout"] = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback):
            return False

        async def post(self, url, headers, json):
            captured["url"] = url
            captured["headers"] = headers
            captured["body"] = json
            return FakeResponse()

    monkeypatch.setattr(llm_client, "PROVIDER", "openai")
    monkeypatch.setattr(llm_client, "API_KEY", "test-key")
    monkeypatch.setattr(llm_client, "MODEL", "gpt-4o-mini")
    monkeypatch.setattr(llm_client, "API_URL", "https://api.openai.com/v1/chat/completions")
    monkeypatch.setattr(llm_client.httpx, "AsyncClient", FakeAsyncClient)

    result = await llm_client.complete_json("system prompt", "user request", max_tokens=700)

    assert result == {"result": "Answer"}
    assert captured["headers"]["Authorization"] == "Bearer test-key"
    assert captured["body"]["response_format"] == {"type": "json_object"}
    assert captured["body"]["model"] == "gpt-4o-mini"
    assert captured["body"]["max_tokens"] == 700
