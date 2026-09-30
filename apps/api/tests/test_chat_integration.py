import os
import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_INTEGRATION_TESTS") != "1",
    reason="integration services are not enabled",
)


def _register(client: TestClient, label: str) -> str:
    response = client.post(
        "/auth/register",
        json={
            "email": f"{label}-{uuid.uuid4()}@example.com",
            "password": "AgentOps-secure-pass-2026",
            "organization_name": f"{label} Operations",
        },
    )
    assert response.status_code == 201
    return response.json()["access_token"]


def test_streamed_chat_persists_memory_and_structured_citations() -> None:
    with TestClient(app) as client:
        token = _register(client, "chat-owner")
        headers = {"Authorization": f"Bearer {token}"}

        upload = client.post(
            "/documents",
            headers=headers,
            files={
                "file": (
                    "incident-runbook.md",
                    (
                        b"Authentication incident runbook. If refresh token "
                        b"replay is detected, revoke the affected session, "
                        b"inspect request logs, rotate exposed credentials, "
                        b"and verify that tenant boundaries still hold."
                    ),
                    "text/markdown",
                )
            },
        )
        assert upload.status_code == 201

        conversation = client.post(
            "/chat/conversations",
            headers=headers,
            json={},
        )
        assert conversation.status_code == 201
        conversation_id = conversation.json()["id"]

        streamed = client.post(
            f"/chat/conversations/{conversation_id}/messages/stream",
            headers=headers,
            json={"content": "What should we do after refresh token replay?"},
        )

        assert streamed.status_code == 200
        assert streamed.headers["content-type"].startswith("text/event-stream")
        assert "event: sources" in streamed.text
        assert "incident-runbook.md" in streamed.text
        assert "event: token" in streamed.text
        assert "event: done" in streamed.text

        messages = client.get(
            f"/chat/conversations/{conversation_id}/messages",
            headers=headers,
        )
        assert messages.status_code == 200
        payload = messages.json()

        assert len(payload) == 2
        assert payload[0]["role"] == "user"
        assert payload[1]["role"] == "assistant"
        assert payload[1]["citations"]
        assert payload[1]["citations"][0]["filename"] == "incident-runbook.md"

        second = client.post(
            f"/chat/conversations/{conversation_id}/messages/stream",
            headers=headers,
            json={"content": "And what logs should be checked?"},
        )
        assert second.status_code == 200
        assert "event: done" in second.text

        memory = client.get(
            f"/chat/conversations/{conversation_id}/messages",
            headers=headers,
        )
        assert memory.status_code == 200
        assert len(memory.json()) == 4


def test_conversations_are_private_to_the_creating_user() -> None:
    with TestClient(app) as first_client:
        first_token = _register(first_client, "chat-first")
        first_headers = {"Authorization": f"Bearer {first_token}"}

        conversation = first_client.post(
            "/chat/conversations",
            headers=first_headers,
            json={"title": "Private conversation"},
        )
        assert conversation.status_code == 201
        conversation_id = conversation.json()["id"]

    with TestClient(app) as second_client:
        second_token = _register(second_client, "chat-second")
        second_headers = {"Authorization": f"Bearer {second_token}"}

        response = second_client.get(
            f"/chat/conversations/{conversation_id}/messages",
            headers=second_headers,
        )
        assert response.status_code == 404
