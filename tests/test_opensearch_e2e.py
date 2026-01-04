"""
OpenSearch/Elasticsearch 稀疏检索集成测试（可选）

运行条件：
  - 启动一个 OpenSearch/ES 实例，提供 HTTP 端点。
  - 设置环境变量：
        RUN_ES_E2E=1
        ES_HOSTS=http://localhost:9200
        API_BASE=http://localhost:8020
        API_KEY=kb_sk_xxx
        KB_ID=<知识库ID>
  - bm25_backend 配置为 es，或服务端已可访问 ES。
"""

import os
import pytest
import httpx

pytestmark = pytest.mark.e2e


def _require_env(name: str) -> str:
    val = os.getenv(name)
    if not val:
        pytest.skip(f"{name} not set")
    return val


@pytest.mark.asyncio
async def test_es_retrieve_e2e():
    if not os.getenv("RUN_ES_E2E"):
        pytest.skip("RUN_ES_E2E not set")
    api_base = _require_env("API_BASE")
    api_key = _require_env("API_KEY")
    kb_id = _require_env("KB_ID")

    headers = {"Authorization": f"Bearer {api_key}"}
    payload = {
        "query": "集成测试",
        "knowledge_base_ids": [kb_id],
        "top_k": 3,
        "retriever_override": {"name": "bm25"},
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(f"{api_base}/v1/retrieve", headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
        assert "results" in data


@pytest.mark.asyncio
async def test_es_ready_status():
    if not os.getenv("RUN_ES_E2E"):
        pytest.skip("RUN_ES_E2E not set")
    api_base = _require_env("API_BASE")
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(f"{api_base}/ready")
        resp.raise_for_status()
        checks = resp.json().get("checks", {})
        assert "es" in checks
