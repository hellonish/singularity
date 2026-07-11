from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient


def _require_live_groq_tests() -> None:
    if os.getenv("SINGULARITY_RUN_LIVE_TESTS") != "1":
        pytest.skip("Set SINGULARITY_RUN_LIVE_TESTS=1 to allow live Groq tests")


def test_credential_is_encrypted_and_never_returned(
    client: TestClient,
    current_user: dict[str, str],
) -> None:
    secret = "gsk_test_not_a_real_key"
    response = client.post(
        "/llm/credentials",
        json={"provider": "groq", "api_key": secret, "default_model_id": "openai/gpt-oss-20b"},
        headers=current_user,
    )
    assert response.status_code == 201, response.text
    assert "api_key" not in response.json()
    assert secret not in response.text


@pytest.mark.integration
def test_live_groq_byok_credential_discovery_and_completion(
    client: TestClient,
    current_user: dict[str, str],
) -> None:
    """Exercise the real Groq API; never runs without an explicit test key."""

    _require_live_groq_tests()
    api_key = os.getenv("SINGULARITY_TEST_GROQ_API_KEY")
    if not api_key:
        pytest.skip("Set SINGULARITY_TEST_GROQ_API_KEY to run live Groq integration tests")

    credential = client.post(
        "/llm/credentials",
        json={"provider": "groq", "api_key": api_key},
        headers=current_user,
    )
    assert credential.status_code == 201, credential.text
    credential_id = credential.json()["id"]

    models = client.get(
        f"/llm/credentials/{credential_id}/models",
        headers=current_user,
    )
    assert models.status_code == 200, models.text
    model_ids = {model["id"] for model in models.json()}
    assert model_ids

    # Keep the real request cheap. The chosen model must first be confirmed by
    # the authenticated Models API rather than assumed from a static list.
    selected_model = "openai/gpt-oss-20b"
    if selected_model not in model_ids:
        pytest.skip(f"{selected_model} is not available for this Groq credential")

    completion = client.post(
        "/llm/completions",
        json={
            "message": "Return a JSON object matching the required schema with answer set to pong.",
            "provider_credential_id": credential_id,
            "model_id": selected_model,
            "max_output_tokens": 128,
            "structured_output": {
                "name": "answer",
                "schema": {
                    "type": "object",
                    "properties": {"answer": {"type": "string"}},
                    "required": ["answer"],
                    "additionalProperties": False,
                },
            },
        },
        headers=current_user,
    )
    assert completion.status_code == 200, completion.text
    assert completion.json()["model_id"] == selected_model
    assert completion.json()["structured_output"]["answer"].strip()


@pytest.mark.integration
def test_live_invalid_groq_credential_is_mapped_to_a_safe_error(
    client: TestClient,
    current_user: dict[str, str],
) -> None:
    _require_live_groq_tests()
    credential = client.post(
        "/llm/credentials",
        json={"provider": "groq", "api_key": "gsk_intentionally_invalid_integration_test_key"},
        headers=current_user,
    )
    assert credential.status_code == 201, credential.text

    response = client.get(f"/llm/credentials/{credential.json()['id']}/models", headers=current_user)
    assert response.status_code == 422, response.text
    assert response.json()["detail"] == {
        "code": "provider_credential_invalid",
        "message": "The saved Groq credential is invalid or expired",
        "retryable": False,
    }
