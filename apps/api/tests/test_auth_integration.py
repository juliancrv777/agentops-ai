import os
import uuid

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_INTEGRATION_TESTS") != "1",
    reason="integration services are not enabled",
)

settings = get_settings()


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_auth_rotation_and_tenant_boundary() -> None:
    email = f"owner-{uuid.uuid4()}@example.com"
    password = "AgentOps-secure-pass-2026"

    with TestClient(app) as client:
        register_response = client.post(
            "/auth/register",
            json={
                "email": email,
                "password": password,
                "display_name": "AgentOps Owner",
                "organization_name": "Acme Operations",
            },
        )

        assert register_response.status_code == 201
        access_token = register_response.json()["access_token"]
        original_refresh = client.cookies.get(settings.refresh_cookie_name)
        assert original_refresh

        me_response = client.get("/auth/me", headers=_bearer(access_token))
        assert me_response.status_code == 200
        me = me_response.json()
        assert me["email"] == email
        assert me["role"] == "owner"

        organization_id = me["organization_id"]

        own_org_response = client.get(
            f"/organizations/{organization_id}",
            headers=_bearer(access_token),
        )
        assert own_org_response.status_code == 200
        assert own_org_response.json()["id"] == organization_id

        cross_tenant_response = client.get(
            f"/organizations/{uuid.uuid4()}",
            headers=_bearer(access_token),
        )
        assert cross_tenant_response.status_code == 403

        refresh_response = client.post("/auth/refresh")
        assert refresh_response.status_code == 200
        rotated_refresh = client.cookies.get(settings.refresh_cookie_name)
        assert rotated_refresh
        assert rotated_refresh != original_refresh

        replay_response = client.post(
            "/auth/refresh",
            headers={
                "Cookie": f"{settings.refresh_cookie_name}={original_refresh}",
            },
        )
        assert replay_response.status_code == 401

        bad_login = client.post(
            "/auth/login",
            json={"email": email, "password": "wrong-password"},
        )
        assert bad_login.status_code == 401

        login_response = client.post(
            "/auth/login",
            json={"email": email, "password": password},
        )
        assert login_response.status_code == 200

        logout_response = client.post("/auth/logout")
        assert logout_response.status_code == 204
        assert client.cookies.get(settings.refresh_cookie_name) is None

        refresh_after_logout = client.post("/auth/refresh")
        assert refresh_after_logout.status_code == 401


def test_duplicate_registration_is_rejected() -> None:
    email = f"duplicate-{uuid.uuid4()}@example.com"
    payload = {
        "email": email,
        "password": "AgentOps-secure-pass-2026",
        "organization_name": "Duplicate Test",
    }

    with TestClient(app) as client:
        first = client.post("/auth/register", json=payload)
        second = client.post("/auth/register", json=payload)

    assert first.status_code == 201
    assert second.status_code == 409
