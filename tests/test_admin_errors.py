import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.config import get_settings


@pytest.fixture(autouse=True)
def _set_admin_token():
    settings = get_settings()
    settings.admin_token = "secret-admin"
    yield


def test_admin_missing_token_returns_code():
    client = TestClient(app)
    resp = client.get("/admin/tenants")
    assert resp.status_code == 401
    assert resp.json() == {
        "code": "MISSING_ADMIN_TOKEN",
        "detail": "Missing X-Admin-Token header",
    }


def test_admin_invalid_token_returns_code():
    client = TestClient(app)
    resp = client.get("/admin/tenants", headers={"X-Admin-Token": "wrong"})
    assert resp.status_code == 403
    assert resp.json() == {
        "code": "INVALID_ADMIN_TOKEN",
        "detail": "Invalid admin token",
    }
