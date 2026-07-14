from __future__ import annotations

import asyncio
import os
import tempfile
from collections.abc import Generator
from pathlib import Path

from dotenv import load_dotenv

# Load developer-only integration credentials before isolating application state.
load_dotenv()

# Unit tests never emit developer conversation data to external observability.
# A dedicated opt-in integration test can override this value explicitly.
os.environ["LANGSMITH_TRACING"] = "false"

# These values must exist before API modules are imported during test collection.
TEST_ROOT = Path(tempfile.mkdtemp(prefix="singularity-tests-"))
os.environ["SINGULARITY_DATABASE_URL"] = f"sqlite+aiosqlite:///{TEST_ROOT / 'test.db'}"
os.environ["SINGULARITY_STORAGE_ROOT"] = str(TEST_ROOT / "objects")
os.environ["SINGULARITY_CREDENTIAL_ENCRYPTION_KEY"] = "RE4M2MdV8AqhOY9WcOIbqCcJw_leyZsDR_2p3HnQp98="
os.environ["SINGULARITY_SSE_DUMMY_DELAY_SECONDS"] = "0"
# The deterministic suite uses the X-User-ID identity boundary; dedicated auth
# tests exercise the bearer/JWT path explicitly by overriding these.
os.environ["SINGULARITY_AUTH_MODE"] = "header"
os.environ.setdefault("SINGULARITY_JWT_SECRET", "test-jwt-secret-not-for-production")

import pytest
from fastapi.testclient import TestClient

from api.database import engine
from api.main import app
from api.models import Base


async def _reset_database() -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)


@pytest.fixture(autouse=True)
def reset_database() -> Generator[None, None, None]:
    asyncio.run(_reset_database())
    yield


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def current_user(client: TestClient) -> dict[str, str]:
    response = client.post("/users", json={"display_name": "Test User"})
    assert response.status_code == 201, response.text
    return {"X-User-ID": response.json()["id"]}
