"""Hosted API transport for the distributable Singularity CLI.

The shipped CLI has one user-managed secret: the selected provider's BYOK key.
Everything else is bootstrapped automatically against the hosted API. A random
device token gives the installation a renewable bearer session, while provider
credentials are matched by their one-way fingerprint before being uploaded.
"""
from __future__ import annotations

import hashlib
import json
import os
import secrets
from collections.abc import AsyncIterator
from dataclasses import dataclass, replace
from typing import Any, Protocol

import httpx

from engine.cli.settings import TerminalSettings


DEFAULT_API_URL = "https://singularity.hellonish.dev/api"
LOCAL_FALLBACK_API_URL = "http://127.0.0.1:8000"


class SettingsStore(Protocol):
    def load(self) -> TerminalSettings: ...
    def save(self, settings: TerminalSettings) -> None: ...


@dataclass(frozen=True)
class APIEvent:
    event: str
    data: dict[str, Any]
    event_id: str | None = None


class SingularityAPIError(RuntimeError):
    def __init__(self, message: str, *, status_code: int | None = None, code: str | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code


class SingularityAPIClient:
    """Authenticated async client with automatic device login and token refresh."""

    def __init__(
        self,
        settings_store: SettingsStore,
        *,
        base_url: str | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
        timeout: float = 30.0,
    ) -> None:
        self._settings_store = settings_store
        configured_url = base_url or os.getenv("SINGULARITY_API_URL")
        # An explicit target is intentional: never silently redirect its
        # credentials to another server. The shipped default can fall back to a
        # checkout's local API when the deployment has not caught up with the
        # CLI auth contract.
        self._can_fallback_to_local = configured_url is None
        self.base_url = (configured_url or DEFAULT_API_URL).rstrip("/")
        self.fell_back_to_local = False
        self._transport = transport
        self._timeout = timeout
        self._access_token = ""

    def _client(self, *, timeout: float | None = None) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            # Preserve deployment prefixes such as /api when joining paths.
            base_url=f"{self.base_url}/",
            transport=self._transport,
            timeout=self._timeout if timeout is None else timeout,
            headers={"User-Agent": "singularity-cli/1"},
        )

    def _save_auth(self, *, device_token: str, refresh_token: str) -> None:
        current = self._settings_store.load()
        self._settings_store.save(replace(
            current,
            api_device_token=device_token,
            api_refresh_token=refresh_token,
        ))

    def _use_local_fallback(self) -> bool:
        if not self._can_fallback_to_local or self.base_url == LOCAL_FALLBACK_API_URL:
            return False
        self.base_url = LOCAL_FALLBACK_API_URL
        self._access_token = ""
        self.fell_back_to_local = True
        return True

    async def _request_device_session(self, device_token: str) -> httpx.Response:
        """Start a device session, retrying the default deployment against localhost.

        This deliberately applies only to the unauthenticated bootstrap route.
        Once a caller explicitly sets ``SINGULARITY_API_URL``, its endpoint is
        authoritative and no credential-bearing request is redirected.
        """
        try:
            async with self._client() as client:
                response = await client.post(
                    "auth/cli-device",
                    json={"device_token": device_token},
                )
        except httpx.RequestError:
            if not self._use_local_fallback():
                raise
            async with self._client() as client:
                return await client.post(
                    "auth/cli-device",
                    json={"device_token": device_token},
                )

        if response.status_code in {400, 404, 405} and self._use_local_fallback():
            async with self._client() as client:
                return await client.post(
                    "auth/cli-device",
                    json={"device_token": device_token},
                )
        return response

    async def _authenticate(self, *, force: bool = False) -> str:
        if self._access_token and not force:
            return self._access_token
        self._access_token = ""
        settings = self._settings_store.load()
        device_token = settings.api_device_token or secrets.token_urlsafe(48)

        if settings.api_refresh_token:
            try:
                async with self._client() as client:
                    response = await client.post(
                        "auth/refresh",
                        json={"refresh_token": settings.api_refresh_token},
                    )
            except httpx.RequestError:
                # Continue to the device bootstrap below, which can redirect
                # the implicit hosted default to a local development API.
                response = None
            if response is not None and response.is_success:
                payload = response.json()
                self._access_token = str(payload["access_token"])
                self._save_auth(
                    device_token=device_token,
                    refresh_token=str(payload["refresh_token"]),
                )
                return self._access_token

        response = await self._request_device_session(device_token)
        if response.status_code in {400, 404, 405}:
            raise SingularityAPIError(
                "The hosted API is not running the CLI-compatible auth/routes yet. "
                "Deploy this checkout's API, or relaunch with SINGULARITY_CLI_BACKEND=local.",
                status_code=response.status_code,
                code="api_cli_incompatible",
            )
        self._raise_for_response(response, "Could not initialize the CLI API session")
        payload = response.json()
        self._access_token = str(payload["access_token"])
        self._save_auth(
            device_token=device_token,
            refresh_token=str(payload["refresh_token"]),
        )
        return self._access_token

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
    ) -> httpx.Response:
        token = await self._authenticate()
        async with self._client() as client:
            response = await client.request(
                method,
                path.lstrip("/"),
                json=json_body,
                headers={"Authorization": f"Bearer {token}"},
            )
        if response.status_code == 401:
            token = await self._authenticate(force=True)
            async with self._client() as client:
                response = await client.request(
                    method,
                    path.lstrip("/"),
                    json=json_body,
                    headers={"Authorization": f"Bearer {token}"},
                )
        self._raise_for_response(response, f"Singularity API request failed: {method} {path}")
        return response

    @staticmethod
    def _raise_for_response(response: httpx.Response, fallback: str) -> None:
        if response.is_success:
            return
        message = fallback
        code = None
        try:
            detail = response.json().get("detail")
            if isinstance(detail, dict):
                message = str(detail.get("message") or detail.get("error") or fallback)
                code = str(detail.get("code")) if detail.get("code") else None
            elif detail:
                message = str(detail)
        except (ValueError, AttributeError):
            if response.text.strip():
                message = response.text.strip()[:500]
        request = response.request
        location = f"{request.method} {request.url.path}" if request is not None else "API request"
        raise SingularityAPIError(
            f"{message} (HTTP {response.status_code}; {location})",
            status_code=response.status_code,
            code=code,
        )

    async def health(self) -> dict[str, Any]:
        async with self._client() as client:
            response = await client.get("health")
        self._raise_for_response(response, "Singularity API is unavailable")
        return dict(response.json())

    async def ensure_credential(self, *, provider: str, api_key: str, model_id: str) -> str:
        """Return the API credential id matching this BYOK key, creating it once."""
        fingerprint = hashlib.sha256(api_key.encode("utf-8")).hexdigest()
        credentials = (await self._request("GET", "/llm/credentials")).json()
        match = next(
            (
                item for item in credentials
                if item.get("provider") == provider
                and item.get("key_fingerprint") == fingerprint
                and item.get("status") == "active"
            ),
            None,
        )
        if match is None:
            response = await self._request(
                "POST",
                "/llm/credentials",
                json_body={
                    "provider": provider,
                    "api_key": api_key,
                    "label": "Singularity CLI",
                    "default_model_id": model_id,
                },
            )
            match = response.json()
        elif match.get("default_model_id") != model_id:
            match = (await self._request(
                "PATCH",
                f"/llm/credentials/{match['id']}",
                json_body={"default_model_id": model_id},
            )).json()
        credential_id = str(match["id"])
        await self._request(
            "PUT",
            "/llm/selection",
            json_body={"credential_id": credential_id},
        )
        return credential_id

    async def list_models(self, *, provider: str, api_key: str, model_id: str) -> list[dict[str, Any]]:
        credential_id = await self.ensure_credential(
            provider=provider, api_key=api_key, model_id=model_id
        )
        response = await self._request("GET", f"/llm/credentials/{credential_id}/models")
        return list(response.json())

    async def create_chat(self, *, credential_id: str, model_id: str) -> str:
        response = await self._request(
            "POST",
            "/chats",
            json_body={"provider_credential_id": credential_id, "model_id": model_id},
        )
        return str(response.json()["id"])

    async def create_research_run(
        self,
        *,
        query: str,
        credential_id: str,
        model_id: str,
        strength: int,
    ) -> dict[str, Any]:
        response = await self._request(
            "POST",
            "/research/runs",
            json_body={
                "query": query,
                "provider_credential_id": credential_id,
                "model_id": model_id,
                "strength": strength,
                "run_data": {"client": "cli"},
            },
        )
        return dict(response.json())

    async def stream_chat(self, *, chat_id: str, message: str, effort: str) -> AsyncIterator[APIEvent]:
        async for event in self._stream(
            "POST",
            f"/chats/{chat_id}/messages/stream",
            json_body={
                "content": message,
                "message_data": {"client": "cli", "effort": effort},
            },
        ):
            yield event

    async def stream_research(self, run_id: str) -> AsyncIterator[APIEvent]:
        async for event in self._stream("GET", f"/research/runs/{run_id}/events"):
            yield event

    async def stream_report(self, report_id: str) -> AsyncIterator[APIEvent]:
        async for event in self._stream("GET", f"/reports/{report_id}/stream"):
            yield event

    async def _stream(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
    ) -> AsyncIterator[APIEvent]:
        # Research runs may legitimately last an hour; disable the read timeout
        # while retaining connect/write/pool timeouts.
        timeout = httpx.Timeout(connect=self._timeout, write=self._timeout, read=None, pool=self._timeout)
        for attempt in range(2):
            token = await self._authenticate(force=attempt > 0)
            async with self._client(timeout=timeout) as client:
                async with client.stream(
                    method,
                    path.lstrip("/"),
                    json=json_body,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Accept": "text/event-stream",
                    },
                ) as response:
                    if response.status_code == 401 and attempt == 0:
                        continue
                    self._raise_for_response(response, f"Singularity API stream failed: {method} {path}")
                    async for event in _parse_sse(response.aiter_lines()):
                        yield event
                    return


async def _parse_sse(lines: AsyncIterator[str]) -> AsyncIterator[APIEvent]:
    event_name = "message"
    event_id: str | None = None
    data_lines: list[str] = []
    async for line in lines:
        if not line:
            if data_lines:
                raw = "\n".join(data_lines)
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    data = {"content": raw}
                if not isinstance(data, dict):
                    data = {"value": data}
                yield APIEvent(event=event_name, data=data, event_id=event_id)
            event_name = "message"
            event_id = None
            data_lines = []
            continue
        if line.startswith(":"):
            continue
        field, _, value = line.partition(":")
        value = value[1:] if value.startswith(" ") else value
        if field == "event":
            event_name = value
        elif field == "id":
            event_id = value
        elif field == "data":
            data_lines.append(value)
    if data_lines:
        raw = "\n".join(data_lines)
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = {"content": raw}
        if not isinstance(data, dict):
            data = {"value": data}
        yield APIEvent(event=event_name, data=data, event_id=event_id)
