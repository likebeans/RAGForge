"""
向量数据库模块 (Vector Store)

封装 Qdrant 向量数据库的操作，提供：
- 向量存储（upsert）
- 相似度搜索（search）
- 多租户隔离（每租户一个 Collection）

特性：
- 使用 AsyncQdrantClient，不阻塞事件循环
- 使用真实 Embedding（OpenAI/确定性哈希）
- 支持批量操作
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from functools import lru_cache
from typing import Iterable

from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models

from app.config import get_settings
from app.infra.embeddings import get_embedding, get_embeddings

logger = logging.getLogger(__name__)


@dataclass
class VectorRecord:
    """向量记录：封装向量数据库中的一条记录"""
    chunk_id: str           # 片段 ID
    tenant_id: str          # 租户 ID
    knowledge_base_id: str  # 知识库 ID
    text: str               # 原始文本
    metadata: dict          # 元数据


@lru_cache(maxsize=1)
def _get_async_client() -> AsyncQdrantClient:
    """获取异步 Qdrant 客户端（单例）"""
    settings = get_settings()
    return AsyncQdrantClient(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key,
        timeout=10.0,
        prefer_grpc=False,
    )


class AsyncQdrantVectorStore:
    """
    异步 Qdrant 向量存储
    
    多租户隔离策略：每个租户一个独立的 Collection
    Collection 命名：{prefix}{tenant_id}，如 kb_tenant_001
    
    注意：所有方法都是异步的，需要使用 await 调用
    """

    def __init__(self, client: AsyncQdrantClient | None = None):
        self._client = client
        self._settings = get_settings()
        self.dim = self._settings.embedding_dim
        self.collection_prefix = self._settings.qdrant_collection_prefix
        self._collection_cache: set[str] = set()  # 缓存已创建的 collection

    @property
    def client(self) -> AsyncQdrantClient:
        if self._client is None:
            self._client = _get_async_client()
        return self._client

    def _collection_name(self, tenant_id: str) -> str:
        return f"{self.collection_prefix}{tenant_id}"

    async def _ensure_collection(self, tenant_id: str) -> str:
        """确保 Collection 存在（带缓存）"""
        name = self._collection_name(tenant_id)
        
        # 检查缓存
        if name in self._collection_cache:
            return name
        
        try:
            await self.client.get_collection(name)
            self._collection_cache.add(name)
            return name
        except Exception:
            pass
        
        try:
            await self.client.create_collection(
                collection_name=name,
                vectors_config=models.VectorParams(
                    size=self.dim,
                    distance=models.Distance.COSINE,
                ),
            )
            self._collection_cache.add(name)
            logger.info(f"创建 Collection: {name}")
        except Exception as e:
            # 可能被并发请求创建
            logger.debug(f"Collection 可能已存在: {e}")
            self._collection_cache.add(name)
        
        return name

    async def upsert_chunk(
        self,
        *,
        chunk_id: str,
        tenant_id: str,
        knowledge_base_id: str,
        text: str,
        metadata: dict | None = None,
    ) -> None:
        """
        插入/更新单个 chunk
        
        Args:
            chunk_id: Chunk ID
            tenant_id: 租户 ID
            knowledge_base_id: 知识库 ID
            text: 文本内容
            metadata: 额外元数据
        """
        collection = await self._ensure_collection(tenant_id)
        
        # 使用真实 Embedding
        vector = await get_embedding(text)
        
        payload = {
            "kb_id": knowledge_base_id,
            "text": text,
            "metadata": metadata or {},
        }
        
        await self.client.upsert(
            collection_name=collection,
            points=[
                models.PointStruct(
                    id=chunk_id,
                    vector=vector,
                    payload=payload,
                )
            ],
        )

    async def upsert_chunks(
        self,
        *,
        tenant_id: str,
        chunks: list[dict],
    ) -> None:
        """
        批量插入/更新 chunks
        
        Args:
            tenant_id: 租户 ID
            chunks: chunk 列表，每个包含 chunk_id, knowledge_base_id, text, metadata
        """
        if not chunks:
            return
        
        collection = await self._ensure_collection(tenant_id)
        
        # 批量获取 Embedding
        texts = [c["text"] for c in chunks]
        vectors = await get_embeddings(texts)
        
        # 构建 points
        points = [
            models.PointStruct(
                id=chunk["chunk_id"],
                vector=vector,
                payload={
                    "kb_id": chunk["knowledge_base_id"],
                    "text": chunk["text"],
                    "metadata": chunk.get("metadata", {}),
                },
            )
            for chunk, vector in zip(chunks, vectors)
        ]
        
        await self.client.upsert(
            collection_name=collection,
            points=points,
        )
        logger.debug(f"批量 upsert {len(chunks)} chunks 到 {collection}")

    async def search(
        self,
        *,
        query: str,
        tenant_id: str,
        kb_ids: Iterable[str],
        top_k: int = 5,
    ) -> list[tuple[float, VectorRecord]]:
        """
        语义搜索
        
        Args:
            query: 查询文本
            tenant_id: 租户 ID
            kb_ids: 知识库 ID 列表
            top_k: 返回数量
        
        Returns:
            list[tuple[score, VectorRecord]]
        """
        collection = self._collection_name(tenant_id)
        
        # 使用真实 Embedding
        vector = await get_embedding(query)
        
        kb_list = list(kb_ids)
        filter_ = models.Filter(
            must=[
                models.FieldCondition(
                    key="kb_id",
                    match=models.MatchAny(any=kb_list),
                )
            ]
        )
        
        try:
            results = await self.client.search(
                collection_name=collection,
                query_vector=vector,
                query_filter=filter_,
                limit=top_k,
                with_payload=True,
            )
        except Exception as exc:
            logger.error(f"向量搜索失败: {exc}")
            return []

        hits: list[tuple[float, VectorRecord]] = []
        for point in results:
            payload = point.payload or {}
            hits.append(
                (
                    point.score or 0.0,
                    VectorRecord(
                        chunk_id=str(point.id),
                        tenant_id=tenant_id,
                        knowledge_base_id=payload.get("kb_id"),
                        text=payload.get("text", ""),
                        metadata=payload.get("metadata", {}) or {},
                    ),
                )
            )
        return hits

    async def delete_by_kb(self, tenant_id: str, kb_id: str) -> int:
        """
        删除指定知识库的所有向量
        
        Returns:
            删除的数量
        """
        collection = self._collection_name(tenant_id)
        try:
            result = await self.client.delete(
                collection_name=collection,
                points_selector=models.FilterSelector(
                    filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="kb_id",
                                match=models.MatchValue(value=kb_id),
                            )
                        ]
                    )
                ),
            )
            logger.info(f"删除 KB {kb_id} 的向量，状态: {result.status}")
            return 0  # Qdrant 不返回删除数量
        except Exception as e:
            logger.error(f"删除向量失败: {e}")
            return 0

    async def delete_by_ids(self, tenant_id: str, chunk_ids: list[str]) -> int:
        """
        按 ID 列表删除向量
        
        Args:
            tenant_id: 租户 ID
            chunk_ids: Chunk ID 列表
        
        Returns:
            删除的数量（Qdrant 不返回实际数量，返回 0）
        """
        if not chunk_ids:
            return 0
            
        collection = self._collection_name(tenant_id)
        try:
            result = await self.client.delete(
                collection_name=collection,
                points_selector=models.PointIdsList(
                    points=chunk_ids,
                ),
            )
            logger.info(f"删除 {len(chunk_ids)} 个向量，状态: {result.status}")
            return len(chunk_ids)
        except Exception as e:
            logger.error(f"按 ID 删除向量失败: {e}")
            return 0


# 全局实例（异步）
vector_store = AsyncQdrantVectorStore()
