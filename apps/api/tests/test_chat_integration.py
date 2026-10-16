"""End-to-end tenant and ownership guarantees against real Postgres/pgvector."""
import os
import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_INTEGRATION_TESTS") != "1",
    reason="integration services are not enabled",
)


def register(client: TestClient, label: str) -> dict[str, str]:
    response = client.post(
        "/auth/register",
        json={
            "email": f"{label}-{uuid.uuid4()}@example.com",
            "password": "agentops-strong-password-2026",
            "organization_name": label + " Knowledge",
        },
    )
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_conversation_rag_persistence_delete_and_isolation() -> None:
    with TestClient(app) as client:
        owner = register(client, "chat-owner")
        other = register(client, "chat-other")

        unauthenticated = client.get("/chat/conversations")
        assert unauthenticated.status_code == 401

        created = client.post("/chat/conversations", headers=owner, json={
            "title": "Incident response"
        })
        assert created.status_code == 201
        conversation = created.json()["id"]

        for method, url in [
            (client.get, f"/chat/conversations/{conversation}"),
            (client.delete, f"/chat/conversations/{conversation}"),
        ]:
            assert method(url, headers=other).status_code == 404

        other_send = client.post(
            f"/chat/conversations/{conversation}/messages",
            headers=other, json={"content": "secret runbook"},
        )
        assert other_send.status_code == 404
        assert client.get("/chat/conversations", headers=other).json() == []

        no_docs = client.post(
            f"/chat/conversations/{conversation}/messages",
            headers=owner, json={"content": "where is the runbook?"},
        )
        assert no_docs.status_code == 200
        assert no_docs.json()["mode"] == "no_evidence"
        assert no_docs.json()["assistant_message"]["citations"] == []

        upload = client.post(
            "/documents", headers=owner,
            files={"file": (
                "incident-guide.md",
                b"Incident runbook: API saturation requires checking request "
                b"latency and database connection pool before scaling pods.",
                "text/markdown",
            )},
        )
        assert upload.status_code == 201

        answered = client.post(
            f"/chat/conversations/{conversation}/messages",
            headers=owner, json={"content": "What is the API saturation runbook?"},
        )
        assert answered.status_code == 200
        assert answered.json()["mode"] == "extractive"
        citation = answered.json()["assistant_message"]["citations"][0]
        assert citation["filename"] == "incident-guide.md"
        assert citation["document_id"] == upload.json()["id"]
        assert "Incident runbook" in citation["excerpt"]

        detail = client.get(f"/chat/conversations/{conversation}", headers=owner)
        assert detail.status_code == 200
        assert [message["role"] for message in detail.json()["messages"]] == [
            "user", "assistant", "user", "assistant"
        ]
        assert len(client.get("/chat/conversations", headers=owner).json()) == 1
        assert client.delete(f"/chat/conversations/{conversation}", headers=owner).status_code == 204
        assert client.get(f"/chat/conversations/{conversation}", headers=owner).status_code == 404


def test_chat_empty_title_and_empty_message() -> None:
    with TestClient(app) as client:
        owner = register(client, "chat-input")
        bad_title = client.post("/chat/conversations", headers=owner, json={
            "title": "   "
        })
        assert bad_title.status_code == 422
        created = client.post("/chat/conversations", headers=owner, json={})
        assert created.status_code == 201
        invalid = client.post(
            f"/chat/conversations/{created.json()['id']}/messages",
            headers=owner, json={"content": "   "},
        )
        assert invalid.status_code == 422
