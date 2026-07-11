from __future__ import annotations

from api.models import Base, Chat, LLMProviderCredential, User


def test_v2_database_registers_byok_and_chat_selection_relationships() -> None:
    assert "llm_provider_credentials" in Base.metadata.tables
    assert User.llm_credentials.property.uselist is True
    assert Chat.provider_credential.property.uselist is False
    assert LLMProviderCredential.chats.property.uselist is True
