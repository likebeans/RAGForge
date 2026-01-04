import os

import httpx
import pytest


pytestmark = pytest.mark.e2e


def _require_env(var: str) -> str:
    val = os.getenv(var)
    if not val:
        pytest.skip(f"{var} not set")
    return val


@pytest.mark.asyncio
async def test_health_endpoint_alive():
    base = _require_env("API_BASE")
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.get(f"{base}/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("status") == "ok"
