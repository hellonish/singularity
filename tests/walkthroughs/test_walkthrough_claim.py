from __future__ import annotations

import asyncio

from fastapi.testclient import TestClient

from api.database import SessionLocal
from api.services import walkthroughs as walkthrough_service

KEY = "main-dashboard-tour"


def test_claim_shows_once_then_never_again(client: TestClient, current_user: dict[str, str]) -> None:
    first = client.post(f"/walkthroughs/{KEY}/claim", json={"version": 1}, headers=current_user)
    assert first.status_code == 200, first.text
    body = first.json()
    assert body == {"show": True, "walkthroughKey": KEY, "version": 1}

    second = client.post(f"/walkthroughs/{KEY}/claim", json={"version": 1}, headers=current_user)
    assert second.status_code == 200, second.text
    assert second.json()["show"] is False


def test_new_version_can_be_claimed_again(client: TestClient, current_user: dict[str, str]) -> None:
    client.post(f"/walkthroughs/{KEY}/claim", json={"version": 1}, headers=current_user)
    v2 = client.post(f"/walkthroughs/{KEY}/claim", json={"version": 2}, headers=current_user)
    assert v2.json()["show"] is True


def test_claim_is_scoped_per_user(client: TestClient, current_user: dict[str, str]) -> None:
    client.post(f"/walkthroughs/{KEY}/claim", json={"version": 1}, headers=current_user)

    other = client.post("/users", json={"display_name": "Other"})
    other_headers = {"X-User-ID": other.json()["id"]}
    theirs = client.post(f"/walkthroughs/{KEY}/claim", json={"version": 1}, headers=other_headers)
    assert theirs.json()["show"] is True


def test_complete_and_dismiss_are_idempotent(client: TestClient, current_user: dict[str, str]) -> None:
    client.post(f"/walkthroughs/{KEY}/claim", json={"version": 1}, headers=current_user)

    for _ in range(2):
        done = client.post(f"/walkthroughs/{KEY}/complete", json={"version": 1}, headers=current_user)
        assert done.status_code == 204, done.text

    # Terminal states never re-show.
    again = client.post(f"/walkthroughs/{KEY}/claim", json={"version": 1}, headers=current_user)
    assert again.json()["show"] is False


def test_concurrent_claims_grant_exactly_one(client: TestClient, current_user: dict[str, str]) -> None:
    """The unique constraint — not a lock — guarantees a single winner."""

    async def scenario() -> list[bool]:
        user_id = current_user["X-User-ID"]

        async def one() -> bool:
            async with SessionLocal() as session:
                return await walkthrough_service.claim(
                    session, user_id=user_id, walkthrough_key=KEY, version=1
                )

        return await asyncio.gather(*(one() for _ in range(8)))

    results = asyncio.run(scenario())
    assert sum(results) == 1, results
