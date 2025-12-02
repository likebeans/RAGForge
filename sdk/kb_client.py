"""
知识库服务客户端

封装 HTTP API 调用，提供 Pythonic 的接口。
支持上下文管理器，自动管理连接。
"""

from __future__ import annotations

import httpx


class KBClient:
    """
    知识库服务 Python 客户端
    
    使用示例：
        # 方式1：上下文管理器（推荐）
        with KBClient(api_key="kb_sk_xxx") as client:
            kb = client.create_kb("测试")
            client.add_document(kb["id"], "标题", "内容")
        
        # 方式2：手动管理
        client = KBClient(api_key="kb_sk_xxx")
        try:
            kb = client.create_kb("测试")
        finally:
            client.close()
    """
    
    def __init__(self, api_key: str, base_url: str = "http://localhost:8000"):
        """
        初始化客户端
        
        Args:
            api_key: API Key（格式：kb_sk_xxx）
            base_url: 服务地址
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self._client = httpx.Client(
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10.0,
        )

    def create_kb(self, name: str, description: str | None = None) -> dict:
        """创建知识库"""
        resp = self._client.post(
            f"{self.base_url}/v1/knowledge-bases",
            json={"name": name, "description": description},
        )
        resp.raise_for_status()
        return resp.json()

    def add_document(
        self,
        kb_id: str,
        title: str,
        content: str,
        metadata: dict | None = None,
        source: str | None = None,
    ) -> dict:
        resp = self._client.post(
            f"{self.base_url}/v1/knowledge-bases/{kb_id}/documents",
            json={
                "title": title,
                "content": content,
                "metadata": metadata,
                "source": source,
            },
        )
        resp.raise_for_status()
        return resp.json()

    def query(
        self,
        query: str,
        knowledge_base_ids: list[str],
        top_k: int = 5,
    ) -> dict:
        resp = self._client.post(
            f"{self.base_url}/v1/retrieve",
            json={
                "query": query,
                "knowledge_base_ids": knowledge_base_ids,
                "top_k": top_k,
            },
        )
        resp.raise_for_status()
        return resp.json()

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "KBClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
