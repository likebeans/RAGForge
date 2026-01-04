"""
OpenAI 兼容接口与 RAG 集成测试（可选）

运行条件：
    需要已有运行中的服务和可用的 API Key。
    设置环境变量：
        RUN_OPENAI_E2E=1
        API_BASE=http://localhost:8020
        API_KEY=kb_sk_xxx
    可选：
        KB_ID=<知识库ID> （若提供则会执行 /v1/retrieve 和 /v1/rag 测试）
"""

import os
import pytest
import httpx

pytestmark = pytest.mark.e2e


def _get_env(name: str) -> str | None:
    return os.getenv(name)


def _require_env(name: str) -> str:
    val = os.getenv(name)
    if not val:
        pytest.skip(f"{name} not set for e2e test")
    return val


@pytest.mark.asyncio
async def test_embeddings_e2e():
    if not os.getenv("RUN_OPENAI_E2E"):
        pytest.skip("RUN_OPENAI_E2E not set")
    base = _require_env("API_BASE")
    api_key = _require_env("API_KEY")
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{base}/v1/embeddings",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"model": "text-embedding-3-small", "input": "Hello, world!"},
        )
        resp.raise_for_status()
        data = resp.json()
        assert "data" in data and data["data"]
        assert "embedding" in data["data"][0]


@pytest.mark.asyncio
async def test_retrieve_rag_e2e():
    if not os.getenv("RUN_OPENAI_E2E"):
        pytest.skip("RUN_OPENAI_E2E not set")
    base = _require_env("API_BASE")
    api_key = _require_env("API_KEY")
    kb_id = _get_env("KB_ID")
    if not kb_id:
        pytest.skip("KB_ID not set; skip retrieve/rag")

    headers = {"Authorization": f"Bearer {api_key}"}
    payload = {
        "query": "测试查询",
        "knowledge_base_ids": [kb_id],
        "top_k": 1,
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        # retrieve
        r1 = await client.post(f"{base}/v1/retrieve", headers=headers, json=payload)
        r1.raise_for_status()
        resp1 = r1.json()
        assert "results" in resp1

        # rag
        r2 = await client.post(f"{base}/v1/rag", headers=headers, json=payload)
        r2.raise_for_status()
        resp2 = r2.json()
        assert "answer" in resp2
