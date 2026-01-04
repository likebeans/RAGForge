import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.mark.asyncio
async def test_health_es_field_present():
    client = TestClient(app)
    resp = client.get("/ready")
    assert resp.status_code in (200, 503)
    data = resp.json()
    assert "es" in data.get("checks", {})
