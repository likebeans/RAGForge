"""
端到端测试

测试完整的 API 流程：
1. 创建租户和 API Key
2. 创建知识库
3. 上传文档
4. 检索文档

运行方式：
    pytest tests/test_e2e.py -v
"""

import os
from pathlib import Path

import pytest
from httpx import AsyncClient

# 设置测试环境变量（必须在导入 app 模块之前）
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test.db")
os.environ.setdefault("QDRANT_URL", ":memory:")  # 使用内存向量库
os.environ.setdefault("API_KEY_PREFIX", "kb_sk_")

from app.main import app  # noqa: E402
from app.auth.api_key import generate_api_key  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.db.session import SessionLocal, init_models  # noqa: E402
from app.models import APIKey, Tenant  # noqa: E402

pytestmark = pytest.mark.e2e


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环（pytest-asyncio 需要）"""
    import asyncio

    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.mark.asyncio
async def test_end_to_end_flow(tmp_path):
    """端到端测试：创建知识库 → 上传文档 → 检索"""
    # Clean test DB if present
    db_file = Path("./test.db")
    if db_file.exists():
        db_file.unlink()

    await init_models()
    settings = get_settings()

    # Seed tenant and API key
    async with SessionLocal() as session:
        tenant = Tenant(name="test-tenant")
        session.add(tenant)
        await session.flush()
        display, hashed, prefix = generate_api_key(settings.api_key_prefix)
        api_key = APIKey(
            tenant_id=tenant.id,
            name="default",
            prefix=prefix,
            hashed_key=hashed,
            revoked=False,
        )
        session.add(api_key)
        await session.commit()

    headers = {"Authorization": f"Bearer {display}"}

    async with AsyncClient(app=app, base_url="http://test") as client:
        kb_resp = await client.post("/v1/knowledge-bases", json={"name": "kb1"}, headers=headers)
        assert kb_resp.status_code == 200
        kb_id = kb_resp.json()["id"]

        doc_resp = await client.post(
            f"/v1/knowledge-bases/{kb_id}/documents",
            json={"title": "hello", "content": "hello world"},
            headers=headers,
        )
        assert doc_resp.status_code == 200

        ret_resp = await client.post(
            "/v1/retrieve",
            json={"query": "hello", "knowledge_base_ids": [kb_id]},
            headers=headers,
        )
        assert ret_resp.status_code == 200
        results = ret_resp.json()["results"]
        assert results
        assert results[0]["text"]
