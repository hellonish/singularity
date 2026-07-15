from __future__ import annotations

from contextlib import asynccontextmanager

import pytest

from engine.chat import ChatAgentInput, UnifiedChatAgentLoop
from engine.llm.config import LLMRequestConfig
from engine.llm.groq import GroqModel
from engine.observability import LangSmithTracer


class _FakeProvider:
    async def retrieve_model(self, *, api_key, model_id):
        return GroqModel(id=model_id, context_window=8192, max_completion_tokens=1024, active=True)

    async def stream_chat(self, *, api_key, config, messages):
        yield "safe output"


class _RecordingTracer:
    def __init__(self) -> None:
        self.names: list[str] = []

    def text(self, value: str):
        return {"characters": len(value)}

    @asynccontextmanager
    async def span(self, name, **kwargs):
        self.names.append(name)

        class _Span:
            def end(self, outputs):
                return None

        yield _Span()


def test_disabled_langsmith_tracer_records_only_digests(monkeypatch) -> None:
    monkeypatch.delenv("LANGSMITH_TRACING", raising=False)
    monkeypatch.delenv("LANGSMITH_API_KEY", raising=False)
    tracer = LangSmithTracer()

    assert tracer.enabled is False
    assert tracer.text("authorization: super-secret") != "authorization: super-secret"


def test_content_capture_still_redacts_secret_like_text(monkeypatch) -> None:
    monkeypatch.setenv("LANGSMITH_TRACING", "false")
    monkeypatch.setenv("SINGULARITY_LANGSMITH_CAPTURE_CONTENT", "true")
    tracer = LangSmithTracer()

    assert tracer.text("api_key: super-secret") == "api_key:[REDACTED]"


@pytest.mark.asyncio
async def test_chat_agent_emits_lookup_and_model_turn_observability_spans() -> None:
    tracer = _RecordingTracer()
    loop_agent = UnifiedChatAgentLoop(provider=_FakeProvider(), tracer=tracer)
    events = [
        event
        async for event in loop_agent.stream(
            ChatAgentInput(context="reference", message="question"),
            api_key="test",
            config=LLMRequestConfig(provider="groq", credential_id="test", model_id="test", max_output_tokens=128),
            effort="instant",
            modal_enabled=False,
        )
    ]

    assert events[-1].content == "safe output"
    assert tracer.names == ["model_lookup", "model_turn"]
