import asyncio

import pytest
from fastapi import HTTPException

from api.database import SessionLocal
from api.services.retrieval import RetrievalService
from vector_store import DocumentChunk, RetrievalScope


class RecordingVectorStore:
    def __init__(self) -> None:
        self.scope = None

    def search(self, *, scope, query_text, limit=8, min_credibility=0.0):
        self.scope = scope
        return [
            DocumentChunk(
                text="authorized context",
                embedding=[],
                scope=scope,
                source_type="chat_memory",
                document_id="doc_1",
            )
        ]


async def _search_chat(*, store, user_id: str, chat_id: str):
    async with SessionLocal() as session:
        return await RetrievalService(session=session, vector_store=store).search_chat(
            user_id=user_id,
            chat_id=chat_id,
            query="retrieve relevant context",
        )


def test_chat_retrieval_authorizes_chat_then_constructs_user_bound_scope(client, current_user: dict[str, str]) -> None:
    chat = client.post("/chats", json={"title": "Private chat"}, headers=current_user)
    store = RecordingVectorStore()

    results = asyncio.run(
        _search_chat(store=store, user_id=current_user["X-User-ID"], chat_id=chat.json()["id"])
    )

    assert len(results) == 1
    assert store.scope == RetrievalScope(
        user_id=current_user["X-User-ID"], conversation_id=chat.json()["id"]
    )


def test_chat_retrieval_rejects_another_users_chat_before_vector_search(client, current_user: dict[str, str]) -> None:
    other_user = client.post("/users", json={"display_name": "Other"}).json()
    private_chat = client.post("/chats", json={"title": "Other chat"}, headers={"X-User-ID": other_user["id"]})
    store = RecordingVectorStore()

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            _search_chat(
                store=store,
                user_id=current_user["X-User-ID"],
                chat_id=private_chat.json()["id"],
            )
        )

    assert exc.value.status_code == 404
    assert store.scope is None


def test_production_retrieval_skill_entrypoint_keeps_relational_authorization(client, current_user: dict[str, str]) -> None:
    chat = client.post("/chats", json={"title": "Authorized retrieval"}, headers=current_user).json()
    store = RecordingVectorStore()

    async def run():
        async with SessionLocal() as session:
            return await RetrievalService(session=session, vector_store=store).search_authorized_resource(
                user_id=current_user["X-User-ID"],
                resource_type="chat",
                resource_id=chat["id"],
                query="relevant context",
            )

    results = asyncio.run(run())
    assert results[0].text == "authorized context"
    assert store.scope.user_id == current_user["X-User-ID"]
