"""
BM25 内存存储

提供基于 BM25 算法的稀疏检索能力。

特点：
- 纯内存实现，适合开发和小规模数据
- 按租户和知识库维度隔离索引
- 支持增量更新（每次 upsert 后重建索引）

生产环境建议替换为 Elasticsearch 或 OpenSearch。
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable, TYPE_CHECKING, Any
import logging
import asyncio

from rank_bm25 import BM25Okapi

from app.config import get_settings
from app.infra.bm25_es import ElasticBM25Store

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession
    from app.models import Chunk
else:
    # 懒加载依赖，避免模块导入时的循环
    AsyncSession = Any
    Chunk = Any
    try:
        from sqlalchemy import select
        from sqlalchemy.ext.asyncio import AsyncSession as _AsyncSession  # type: ignore
        from app.models import Chunk as _Chunk  # type: ignore
        AsyncSession = _AsyncSession
        Chunk = _Chunk
    except Exception:  # pragma: no cover - 仅在运行时使用
        AsyncSession = Any
        Chunk = Any


@dataclass
class BM25Record:
    """BM25 记录：存储片段的文本和元数据"""
    chunk_id: str           # 片段 ID
    tenant_id: str          # 租户 ID
    knowledge_base_id: str  # 知识库 ID
    text: str               # 原始文本
    metadata: dict          # 元数据


class InMemoryBM25Store:
    """
    内存 BM25 存储
    
    数据结构：
    - _records: (tenant_id, kb_id) -> {chunk_id -> BM25Record}
    - _indexes: (tenant_id, kb_id) -> BM25Okapi 索引
    
    注意：重启后数据丢失，需要从数据库重建
    """

    def __init__(self):
        self.enabled = True
        self._records: dict[tuple[str, str], dict[str, BM25Record]] = defaultdict(dict)
        self._indexes: dict[tuple[str, str], BM25Okapi] = {}

    def set_enabled(self, enabled: bool) -> None:
        """开启/关闭内存 BM25（关闭后所有操作跳过）"""
        self.enabled = enabled

    def upsert_chunk(
        self,
        *,
        chunk_id: str,
        tenant_id: str,
        knowledge_base_id: str,
        text: str,
        metadata: dict | None = None,
    ) -> None:
        if not self.enabled:
            return
        key = (tenant_id, knowledge_base_id)
        rec = BM25Record(
            chunk_id=chunk_id,
            tenant_id=tenant_id,
            knowledge_base_id=knowledge_base_id,
            text=text,
            metadata=metadata or {},
        )
        self._records[key][chunk_id] = rec
        self._rebuild_index(key)

    def upsert_chunks(
        self,
        *,
        tenant_id: str,
        knowledge_base_id: str,
        chunks: list[dict],
    ) -> None:
        """
        批量 upsert，避免逐条重建索引的内存抖动。
        chunks: [{"chunk_id","text","metadata"}]
        """
        if not self.enabled:
            return
        if not chunks:
            return
        key = (tenant_id, knowledge_base_id)
        for c in chunks:
            rec = BM25Record(
                chunk_id=c["chunk_id"],
                tenant_id=tenant_id,
                knowledge_base_id=knowledge_base_id,
                text=c["text"],
                metadata=c.get("metadata") or {},
            )
            self._records[key][rec.chunk_id] = rec
        self._rebuild_index(key)

    def _rebuild_index(self, key: tuple[str, str]) -> None:
        records = list(self._records[key].values())
        if not records:
            self._indexes.pop(key, None)
            return
        tokenized_corpus = [rec.text.split() for rec in records]
        self._indexes[key] = BM25Okapi(tokenized_corpus)

    def delete_by_ids(self, *, tenant_id: str, knowledge_base_id: str, chunk_ids: list[str]) -> None:
        """按 chunk_id 删除并重建索引"""
        if not self.enabled:
            return
        if not chunk_ids:
            return
        key = (tenant_id, knowledge_base_id)
        for cid in chunk_ids:
            self._records[key].pop(cid, None)
        if not self._records[key]:
            self._indexes.pop(key, None)
            self._records.pop(key, None)
            return
        self._rebuild_index(key)

    def delete_by_kb(self, *, tenant_id: str, knowledge_base_id: str) -> None:
        """删除整个知识库索引"""
        if not self.enabled:
            return
        key = (tenant_id, knowledge_base_id)
        self._records.pop(key, None)
        self._indexes.pop(key, None)

    def search(
        self,
        *,
        query: str,
        tenant_id: str,
        kb_ids: Iterable[str],
        top_k: int = 5,
    ) -> list[tuple[float, BM25Record]]:
        if not self.enabled:
            return []
        results: list[tuple[float, BM25Record]] = []
        tokens = query.split()
        for kb_id in kb_ids:
            key = (tenant_id, kb_id)
            index = self._indexes.get(key)
            if not index:
                continue
            scores = index.get_scores(tokens)
            records = list(self._records[key].values())
            scored = sorted(zip(scores, records), key=lambda x: x[0], reverse=True)[:top_k]
            results.extend(scored)
        results.sort(key=lambda x: x[0], reverse=True)
        return results[:top_k]

    # ============== 重建辅助（用于重启/多副本一致性） ==============
    async def rebuild_from_db(
        self,
        *,
        session: "AsyncSession",
        tenant_id: str,
        knowledge_base_id: str,
        limit: int | None = None,
    ) -> int:
        """
        从数据库重建指定 KB 的 BM25 索引。
        
        Args:
            session: AsyncSession
            tenant_id: 租户 ID
            knowledge_base_id: 知识库 ID
            limit: 可选，限制重建的 chunk 数
        Returns:
            重建的 chunk 数
        """
        if not self.enabled:
            return 0
        if AsyncSession is None or Chunk is None:
            raise RuntimeError("SQLAlchemy 未初始化，无法重建 BM25 索引")
        
        stmt = (
            select(Chunk.id, Chunk.text, Chunk.extra_metadata)
            .where(Chunk.tenant_id == tenant_id)
            .where(Chunk.knowledge_base_id == knowledge_base_id)
        )
        if limit:
            stmt = stmt.limit(limit)
        result = await session.execute(stmt)
        rows = result.all()
        payload = [
            {"chunk_id": row.id, "text": row.text, "metadata": row.extra_metadata or {}}
            for row in rows
        ]
        self.upsert_chunks(
            tenant_id=tenant_id, knowledge_base_id=knowledge_base_id, chunks=payload
        )
        return len(payload)

    async def rebuild_all(
        self,
        *,
        session: "AsyncSession",
        tenant_id: str,
    ) -> int:
        """
        重建租户下所有 KB 的 BM25 索引。
        
        Returns:
            重建的 chunk 总数
        """
        if not self.enabled:
            return 0
        if AsyncSession is None or Chunk is None:
            raise RuntimeError("SQLAlchemy 未初始化，无法重建 BM25 索引")
        
        kb_stmt = (
            select(Chunk.knowledge_base_id)
            .where(Chunk.tenant_id == tenant_id)
            .distinct()
        )
        kb_result = await session.execute(kb_stmt)
        kb_ids = [row[0] for row in kb_result.fetchall()]
        total = 0
        for kb_id in kb_ids:
            total += await self.rebuild_from_db(
                session=session,
                tenant_id=tenant_id,
                knowledge_base_id=kb_id,
            )
        return total


# 根据配置决定是否启用 BM25 内存索引
class BM25Facade:
    """
    BM25 前端选择器
    
    根据配置选择内存或 ES 后端。所有方法签名与 InMemoryBM25Store 保持一致。
    """
    def __init__(self):
        self._settings = get_settings()
        self.enabled = self._settings.bm25_enabled
        self.backend_name = self._settings.bm25_backend
        self.backend = InMemoryBM25Store()
        self.backend.set_enabled(self.enabled)

        if self.enabled and self.backend_name == "es":
            try:
                self.backend = ElasticBM25Store()
                logger.info("使用 Elasticsearch 作为 BM25 后端")
            except Exception as exc:
                logger.warning(f"初始化 ES BM25 失败，降级到内存: {exc}")
                self.backend = InMemoryBM25Store()
                self.backend.set_enabled(True)

    async def upsert_chunk(self, **kwargs):
        if not self.enabled:
            return
        if hasattr(self.backend, "upsert_chunk") and asyncio.iscoroutinefunction(self.backend.upsert_chunk):
            return await self.backend.upsert_chunk(**kwargs)  # type: ignore
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: self.backend.upsert_chunk(**kwargs))  # type: ignore

    async def upsert_chunks(self, **kwargs):
        if not self.enabled:
            return
        if hasattr(self.backend, "upsert_chunks") and asyncio.iscoroutinefunction(self.backend.upsert_chunks):
            return await self.backend.upsert_chunks(**kwargs)  # type: ignore
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: self.backend.upsert_chunks(**kwargs))  # type: ignore

    async def delete_by_ids(self, **kwargs):
        if not self.enabled:
            return
        if hasattr(self.backend, "delete_by_ids") and asyncio.iscoroutinefunction(self.backend.delete_by_ids):
            return await self.backend.delete_by_ids(**kwargs)  # type: ignore
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: self.backend.delete_by_ids(**kwargs))  # type: ignore

    async def delete_by_kb(self, **kwargs):
        if not self.enabled:
            return
        if hasattr(self.backend, "delete_by_kb") and asyncio.iscoroutinefunction(self.backend.delete_by_kb):
            return await self.backend.delete_by_kb(**kwargs)  # type: ignore
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: self.backend.delete_by_kb(**kwargs))  # type: ignore

    async def search(self, **kwargs):
        if not self.enabled:
            return []
        if hasattr(self.backend, "search") and asyncio.iscoroutinefunction(self.backend.search):
            return await self.backend.search(**kwargs)  # type: ignore
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: self.backend.search(**kwargs))  # type: ignore

    async def rebuild_from_db(self, **kwargs):
        if not self.enabled:
            return 0
        if hasattr(self.backend, "rebuild_from_db") and asyncio.iscoroutinefunction(self.backend.rebuild_from_db):
            return await self.backend.rebuild_from_db(**kwargs)  # type: ignore
        return 0

    async def rebuild_all(self, **kwargs):
        if not self.enabled:
            return 0
        if hasattr(self.backend, "rebuild_all") and asyncio.iscoroutinefunction(self.backend.rebuild_all):
            return await self.backend.rebuild_all(**kwargs)  # type: ignore
        return 0


bm25_store = BM25Facade()
