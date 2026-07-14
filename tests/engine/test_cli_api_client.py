from __future__ import annotations

import json

import httpx
import pytest

from engine.cli.api_client import LOCAL_FALLBACK_API_URL, SingularityAPIClient, SingularityAPIError
from engine.cli.settings import TerminalSettings


class FakeSettingsStore:
    def __init__(self) -> None:
        self.settings = TerminalSettings()

    def load(self) -> TerminalSettings:
        return self.settings

    def save(self, settings: TerminalSettings) -> None:
        self.settings = settings


def _sse(*events: tuple[str, dict]) -> bytes:
    return "".join(
        f"event: {name}\nid: {index}\ndata: {json.dumps(data)}\n\n"
        for index, (name, data) in enumerate(events, start=1)
    ).encode()


@pytest.mark.asyncio
async def test_client_preserves_the_production_api_path_prefix() -> None:
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.path)
        return httpx.Response(200, json={"status": "ok"})

    client = SingularityAPIClient(
        FakeSettingsStore(),
        base_url="https://host.test/api",
        transport=httpx.MockTransport(handler),
    )

    assert await client.health() == {"status": "ok"}
    assert seen == ["/api/health"]


@pytest.mark.asyncio
async def test_old_hosted_api_gets_an_actionable_compatibility_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/auth/cli-device"
        return httpx.Response(400, json={"detail": "Bad request."})

    client = SingularityAPIClient(
        FakeSettingsStore(),
        base_url="https://host.test/api",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(SingularityAPIError) as exc:
        await client.ensure_credential(provider="groq", api_key="key", model_id="model")

    assert exc.value.code == "api_cli_incompatible"
    assert "Deploy this checkout's API" in str(exc.value)


@pytest.mark.asyncio
async def test_implicit_hosted_api_falls_back_to_localhost_for_device_auth(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SINGULARITY_API_URL", raising=False)
    calls: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.url.host, request.url.path))
        if request.url.host == "singularity.hellonish.dev":
            assert request.url.path == "/api/auth/cli-device"
            return httpx.Response(404)
        assert request.url.host == "127.0.0.1"
        if request.url.path == "/auth/cli-device":
            return httpx.Response(200, json={
                "access_token": "local-access",
                "refresh_token": "local-refresh",
                "expires_in": 900,
                "token_type": "bearer",
            })
        assert request.headers["authorization"] == "Bearer local-access"
        if request.url.path == "/llm/credentials" and request.method == "GET":
            return httpx.Response(200, json=[])
        if request.url.path == "/llm/credentials" and request.method == "POST":
            return httpx.Response(201, json={
                "id": "local-cred",
                "provider": "groq",
                "key_fingerprint": "unused",
                "default_model_id": "model",
                "status": "active",
            })
        if request.url.path == "/llm/selection":
            return httpx.Response(200, json={"credential_id": "local-cred"})
        raise AssertionError(f"unexpected request: {request.method} {request.url.path}")

    client = SingularityAPIClient(FakeSettingsStore(), transport=httpx.MockTransport(handler))
    credential_id = await client.ensure_credential(provider="groq", api_key="key", model_id="model")

    assert credential_id == "local-cred"
    assert client.base_url == LOCAL_FALLBACK_API_URL
    assert client.fell_back_to_local is True
    assert calls[:2] == [
        ("singularity.hellonish.dev", "/api/auth/cli-device"),
        ("127.0.0.1", "/auth/cli-device"),
    ]


@pytest.mark.asyncio
async def test_local_fallback_still_works_when_a_saved_hosted_refresh_session_is_unreachable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SINGULARITY_API_URL", raising=False)
    store = FakeSettingsStore()
    store.settings = TerminalSettings(
        api_device_token="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
        api_refresh_token="stale-hosted-refresh-token",
    )

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "singularity.hellonish.dev":
            if request.url.path == "/api/auth/refresh":
                raise httpx.ConnectError("host is unavailable", request=request)
            assert request.url.path == "/api/auth/cli-device"
            return httpx.Response(404)
        assert request.url.host == "127.0.0.1"
        assert request.url.path == "/auth/cli-device"
        return httpx.Response(200, json={
            "access_token": "local-access",
            "refresh_token": "local-refresh",
            "expires_in": 900,
            "token_type": "bearer",
        })

    client = SingularityAPIClient(store, transport=httpx.MockTransport(handler))

    assert await client._authenticate() == "local-access"
    assert client.base_url == LOCAL_FALLBACK_API_URL
    assert store.settings.api_refresh_token == "local-refresh"


@pytest.mark.asyncio
async def test_client_bootstraps_device_auth_syncs_byok_and_streams_chat() -> None:
    calls: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.method, request.url.path))
        if request.url.path == "/auth/cli-device":
            return httpx.Response(200, json={
                "access_token": "access-1",
                "refresh_token": "refresh-1",
                "expires_in": 900,
                "token_type": "bearer",
            })
        assert request.headers["authorization"] == "Bearer access-1"
        if request.url.path == "/llm/credentials" and request.method == "GET":
            return httpx.Response(200, json=[])
        if request.url.path == "/llm/credentials" and request.method == "POST":
            body = json.loads(request.content)
            assert body["api_key"] == "provider-secret"
            return httpx.Response(201, json={
                "id": "cred-1",
                "provider": "groq",
                "key_fingerprint": "unused",
                "default_model_id": body["default_model_id"],
                "status": "active",
            })
        if request.url.path == "/llm/selection":
            return httpx.Response(200, json={"credential_id": "cred-1"})
        if request.url.path == "/chats":
            return httpx.Response(201, json={"id": "chat-1"})
        if request.url.path == "/chats/chat-1/messages/stream":
            return httpx.Response(200, content=_sse(
                ("message.accepted", {"model_id": "openai/gpt-oss-20b"}),
                ("message.delta", {"delta": "hello "}),
                ("message.delta", {"delta": "world"}),
                ("message.completed", {"content": "hello world"}),
            ), headers={"content-type": "text/event-stream"})
        raise AssertionError(f"unexpected request: {request.method} {request.url.path}")

    store = FakeSettingsStore()
    client = SingularityAPIClient(
        store,
        base_url="https://api.test",
        transport=httpx.MockTransport(handler),
    )
    credential_id = await client.ensure_credential(
        provider="groq",
        api_key="provider-secret",
        model_id="openai/gpt-oss-20b",
    )
    chat_id = await client.create_chat(credential_id=credential_id, model_id="openai/gpt-oss-20b")
    events = [event async for event in client.stream_chat(
        chat_id=chat_id, message="hi", effort="medium"
    )]

    assert "".join(event.data.get("delta", "") for event in events) == "hello world"
    assert store.settings.api_device_token
    assert store.settings.api_refresh_token == "refresh-1"
    assert calls.count(("POST", "/auth/cli-device")) == 1


@pytest.mark.asyncio
async def test_client_streams_research_then_report_without_local_worker_setup() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/auth/cli-device":
            return httpx.Response(200, json={
                "access_token": "access-1",
                "refresh_token": "refresh-1",
                "expires_in": 900,
                "token_type": "bearer",
            })
        if request.url.path == "/research/runs" and request.method == "POST":
            return httpx.Response(202, json={"id": "run-1", "report_id": "report-1"})
        if request.url.path == "/research/runs/run-1/events":
            return httpx.Response(200, content=_sse(
                ("research.progress", {"status": "node_started", "message": "Researching"}),
                ("research.completed", {"status": "completed"}),
            ))
        if request.url.path == "/reports/report-1/stream":
            return httpx.Response(200, content=_sse(
                ("report.started", {"report_id": "report-1"}),
                ("report.delta", {"delta": "# Report\n"}),
                ("report.completed", {"content": "# Report\n"}),
            ))
        raise AssertionError(f"unexpected request: {request.method} {request.url.path}")

    client = SingularityAPIClient(
        FakeSettingsStore(),
        base_url="https://api.test",
        transport=httpx.MockTransport(handler),
    )
    run = await client.create_research_run(
        query="research this",
        credential_id="cred-1",
        model_id="model-1",
        strength=2,
    )
    research_events = [event async for event in client.stream_research(run["id"])]
    report_events = [event async for event in client.stream_report(run["report_id"])]

    assert research_events[-1].event == "research.completed"
    assert report_events[-1].data["content"] == "# Report\n"
