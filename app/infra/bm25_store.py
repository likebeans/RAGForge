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
from typing import Iterable

from rank_bm25 import BM25Okapi


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
        self._records: dict[tuple[str, str], dict[str, BM25Record]] = defaultdict(dict)
        self._indexes: dict[tuple[str, str], BM25Okapi] = {}

    def upsert_chunk(
        self,
        *,
        chunk_id: str,
        tenant_id: str,
        knowledge_base_id: str,
        text: str,
        metadata: dict | None = None,
    ) -> None:
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


bm25_store = InMemoryBM25Store()
