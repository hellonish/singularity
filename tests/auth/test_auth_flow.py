from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient

from api.config import settings
from api.database import SessionLocal
from api.services import auth as auth_service
from api.services.users import create_user
from api.schemas import UserCreate


@pytest.fixture
def bearer_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "auth_mode", "bearer")
    monkeypatch.setattr(settings, "jwt_secret", "unit-test-secret")
    monkeypatch.setattr(settings, "google_client_id", "test-client-id")


async def _seed_user() -> str:
    async with SessionLocal() as session:
        user = await create_user(session, UserCreate(display_name="Auth User", email="a@example.com"))
        return user.id


def test_access_token_round_trip(bearer_mode: None) -> None:
    user_id = asyncio.run(_seed_user())
    token, expires_in = auth_service.create_access_token(user_id)
    assert expires_in == settings.access_token_ttl_seconds
    assert auth_service.decode_access_token(token) == user_id


def test_bearer_dependency_authenticates_protected_route(
    client: TestClient, bearer_mode: None
) -> None:
    user_id = asyncio.run(_seed_user())
    token, _ = auth_service.create_access_token(user_id)

    ok = client.get("/chats", headers={"Authorization": f"Bearer {token}"})
    assert ok.status_code == 200, ok.text

    missing = client.get("/chats")
    assert missing.status_code == 401

    bad = client.get("/chats", headers={"Authorization": "Bearer not-a-jwt"})
    assert bad.status_code == 401


def test_refresh_rotation_and_reuse_detection(bearer_mode: None) -> None:
    async def scenario() -> None:
        async with SessionLocal() as session:
            user = await create_user(session, UserCreate(display_name="Rotate", email="r@example.com"))
            family = "fam-1"
            first = await auth_service._issue_refresh_token(session, user.id, family)
            await session.commit()

        async with SessionLocal() as session:
            _access, second, _ttl = await auth_service.refresh(session, first)

        # The rotated (first) token is now revoked; presenting it again is reuse.
        async with SessionLocal() as session:
            with pytest.raises(Exception) as reuse:
                await auth_service.refresh(session, first)
            assert reuse.value.status_code == 401

        # Reuse detection revokes the whole family, so the freshly-issued second
        # token is also dead.
        async with SessionLocal() as session:
            with pytest.raises(Exception) as revoked:
                await auth_service.refresh(session, second)
            assert revoked.value.status_code == 401

    asyncio.run(scenario())


def test_logout_revokes_the_token(bearer_mode: None) -> None:
    async def scenario() -> None:
        async with SessionLocal() as session:
            user = await create_user(session, UserCreate(display_name="Bye", email="b@example.com"))
            token = await auth_service._issue_refresh_token(session, user.id, "fam-logout")
            await session.commit()

        async with SessionLocal() as session:
            await auth_service.logout(session, token)

        async with SessionLocal() as session:
            with pytest.raises(Exception) as exc:
                await auth_service.refresh(session, token)
            assert exc.value.status_code == 401

    asyncio.run(scenario())


def test_google_login_upserts_user_and_issues_tokens(
    client: TestClient, bearer_mode: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        auth_service.google_id_token,
        "verify_oauth2_token",
        lambda token, request, client_id: {
            "sub": "google-subject-123",
            "email": "guser@example.com",
            "name": "G User",
        },
    )

    first = client.post("/auth/google", json={"id_token": "fake"})
    assert first.status_code == 200, first.text
    payload = first.json()
    assert payload["token_type"] == "bearer"
    assert payload["access_token"] and payload["refresh_token"]

    # The access token authenticates a protected route.
    protected = client.get("/chats", headers={"Authorization": f"Bearer {payload['access_token']}"})
    assert protected.status_code == 200, protected.text

    # A second login for the same Google subject reuses the same user.
    second = client.post("/auth/google", json={"id_token": "fake"})
    assert second.status_code == 200, second.text

    # The refresh endpoint rotates the token.
    rotated = client.post("/auth/refresh", json={"refresh_token": payload["refresh_token"]})
    assert rotated.status_code == 200, rotated.text
    assert rotated.json()["refresh_token"] != payload["refresh_token"]


def test_cli_device_login_is_zero_interaction_and_stable(
    client: TestClient, bearer_mode: None
) -> None:
    device_token = "device-secret-with-at-least-thirty-two-characters"

    first = client.post("/auth/cli-device", json={"device_token": device_token})
    assert first.status_code == 200, first.text
    first_pair = first.json()
    protected = client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {first_pair['access_token']}"},
    )
    assert protected.status_code == 200, protected.text
    first_user_id = protected.json()["id"]

    second = client.post("/auth/cli-device", json={"device_token": device_token})
    assert second.status_code == 200, second.text
    second_user = client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {second.json()['access_token']}"},
    )
    assert second_user.json()["id"] == first_user_id
    assert device_token not in second.text
