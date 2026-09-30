import os
import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_INTEGRATION_TESTS") != "1",
    reason="integration services are not enabled",
)


def _register(client: TestClient, label: str) -> tuple[str, str]:
    response = client.post(
        "/auth/register",
        json={
            "email": f"{label}-{uuid.uuid4()}@example.com",
            "password": "AgentOps-secure-pass-2026",
            "organization_name": f"{label} Operations",
        },
    )
    assert response.status_code == 201
    token = response.json()["access_token"]

    me = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me.status_code == 200
    return token, me.json()["organization_id"]


def test_document_ingestion_vector_search_and_tenant_isolation() -> None:
    content = (
        b"Payment webhook retry policy. Failed payment webhooks are retried "
        b"every thirty seconds for the first five attempts. Operators should "
        b"inspect the delivery logs before manually replaying an event. "
        b"Idempotency keys prevent duplicate financial side effects."
    )

    with TestClient(app) as owner_client:
        owner_token, _ = _register(owner_client, "retrieval-owner")
        owner_headers = {"Authorization": f"Bearer {owner_token}"}

        upload = owner_client.post(
            "/documents",
            headers=owner_headers,
            files={
                "file": (
                    "payment-runbook.md",
                    content,
                    "text/markdown",
                )
            },
        )

        assert upload.status_code == 201
        document = upload.json()
        assert document["filename"] == "payment-runbook.md"
        assert document["status"] == "ready"

        duplicate = owner_client.post(
            "/documents",
            headers=owner_headers,
            files={
                "file": (
                    "duplicate.md",
                    content,
                    "text/markdown",
                )
            },
        )
        assert duplicate.status_code == 409

        listing = owner_client.get("/documents", headers=owner_headers)
        assert listing.status_code == 200
        assert any(item["id"] == document["id"] for item in listing.json())

        retrieval = owner_client.post(
            "/retrieval/search",
            headers=owner_headers,
            json={
                "query": "payment webhook retry policy and idempotency",
                "top_k": 3,
            },
        )

        assert retrieval.status_code == 200
        results = retrieval.json()["results"]
        assert results
        assert results[0]["filename"] == "payment-runbook.md"
        assert "webhook" in results[0]["content"].lower()
        assert results[0]["metadata"]["source"] == "payment-runbook.md"

    with TestClient(app) as other_client:
        other_token, _ = _register(other_client, "retrieval-other")
        other_headers = {"Authorization": f"Bearer {other_token}"}

        isolated = other_client.post(
            "/retrieval/search",
            headers=other_headers,
            json={
                "query": "payment webhook retry policy",
                "top_k": 3,
            },
        )

        assert isolated.status_code == 200
        assert isolated.json()["results"] == []
