import os
import uuid

import httpx
import pytest


API_BASE = os.getenv("API_BASE", "http://localhost:8000")
API_KEY = os.getenv("API_KEY")

pytestmark = pytest.mark.skipif(
    not API_KEY,
    reason="Set API_KEY env pointing to a valid Bearer token.",
)


def _client():
    return httpx.Client(
        base_url=API_BASE,
        headers={"Authorization": f"Bearer {API_KEY}"},
        timeout=10.0,
        trust_env=False,  # 避免环境代理影响本地容器访问
    )


def test_live_end_to_end():
    kb_name = f"kb-{uuid.uuid4().hex[:8]}"

    with _client() as client:
        # Create KB
        kb_resp = client.post("/v1/knowledge-bases", json={"name": kb_name})
        kb_resp.raise_for_status()
        kb_id = kb_resp.json()["id"]

        # Ingest document
        doc_resp = client.post(
            f"/v1/knowledge-bases/{kb_id}/documents",
            json={"title": "hello", "content": "hello world"},
        )
        doc_resp.raise_for_status()

        # Retrieve
        ret_resp = client.post(
            "/v1/retrieve",
            json={"query": "hello", "knowledge_base_ids": [kb_id], "top_k": 3},
        )
        ret_resp.raise_for_status()
        data = ret_resp.json()
        assert data["results"], "Expected at least one retrieval result"
