"""
Elasticsearch/OpenSearch BM25 存储

用于替换内存 BM25，适合生产多副本场景。
"""

from __future__ import annotations

import logging
import time
from typing import Iterable

from elasticsearch import AsyncElasticsearch, helpers

from app.config import get_settings
from app.infra.logging import get_logger, RequestTimer
from app.infra.metrics import metrics_collector

logger = get_logger(__name__)


def compute_index_name(prefix: str, mode: str, tenant_id: str, kb_id: str) -> str:
    """根据模式生成索引名"""
    if mode == "per_kb":
        return f"{prefix}{tenant_id}_{kb_id}".lower()
    return f"{prefix}shared".lower()


class ElasticBM25Store:
    def __init__(self):
        settings = get_settings()
        if not settings.es_hosts:
            raise RuntimeError("ES_HOSTS 未配置，无法启用 Elasticsearch BM25")
        hosts = [h.strip() for h in settings.es_hosts.split(",") if h.strip()]
        self.client = AsyncElasticsearch(
            hosts=hosts,
            basic_auth=(settings.es_username, settings.es_password) if settings.es_username else None,
            verify_certs=True,
            request_timeout=settings.es_request_timeout,
            max_retries=settings.es_max_retries,
            retry_on_timeout=True,
        )
        self.index_prefix = settings.es_index_prefix or "kb_"
        self.index_mode = settings.es_index_mode or "shared"
        self.bulk_batch_size = settings.es_bulk_batch_size or 500
        self.analyzer = settings.es_analyzer or "standard"
        self.refresh = settings.es_refresh or "false"

    def _index_name(self, tenant_id: str, kb_id: str) -> str:
        return compute_index_name(self.index_prefix, self.index_mode, tenant_id, kb_id)

    async def _ensure_index(self, index: str):
        exists = await self.client.indices.exists(index=index)
        if exists:
            return
        try:
            await self.client.indices.create(
                index=index,
                mappings={
                    "properties": {
                        "text": {"type": "text", "analyzer": self.analyzer},
                        "metadata": {"type": "object", "enabled": True},
                        "tenant_id": {"type": "keyword"},
                        "kb_id": {"type": "keyword"},
                        "doc_id": {"type": "keyword"},
                        "chunk_id": {"type": "keyword"},
                        "created_at": {"type": "date"},
                    }
                },
                settings={
                    "number_of_shards": 1,
                    "number_of_replicas": 0,
                },
            )
            logger.info(f"Created ES index {index}")
        except Exception as exc:
            logger.warning(f"Create index {index} failed (maybe exists): {exc}")

    async def upsert_chunks(
        self,
        *,
        tenant_id: str,
        knowledge_base_id: str,
        chunks: list[dict],
    ) -> None:
        index = self._index_name(tenant_id, knowledge_base_id)
        await self._ensure_index(index)
        if not chunks:
            return
        actions = []
        for c in chunks:
            actions.append(
                {
                    "_op_type": "index",
                    "_index": index,
                    "_id": c["chunk_id"],
                    "_source": {
                        "text": c["text"],
                        "metadata": c.get("metadata") or {},
                        "tenant_id": tenant_id,
                        "kb_id": knowledge_base_id,
                        "doc_id": (c.get("metadata") or {}).get("document_id"),
                        "chunk_id": c["chunk_id"],
                        "created_at": c.get("created_at"),
                    },
                }
            )
        await helpers.async_bulk(
            self.client,
            actions,
            raise_on_error=False,
            chunk_size=self.bulk_batch_size,
            refresh=self.refresh,
        )

    async def delete_by_ids(
        self,
        *,
        tenant_id: str,
        knowledge_base_id: str,
        chunk_ids: list[str],
    ) -> None:
        if not chunk_ids:
            return
        index = self._index_name(tenant_id, knowledge_base_id)
        actions = [
            {"_op_type": "delete", "_index": index, "_id": cid}
            for cid in chunk_ids
        ]
        await helpers.async_bulk(self.client, actions, raise_on_error=False)

    async def delete_by_kb(self, *, tenant_id: str, knowledge_base_id: str) -> None:
        index = self._index_name(tenant_id, knowledge_base_id)
        exists = await self.client.indices.exists(index=index)
        if exists:
            await self.client.indices.delete(index=index, ignore_unavailable=True)

    async def search(
        self,
        *,
        query: str,
        tenant_id: str,
        kb_ids: Iterable[str],
        top_k: int = 5,
    ) -> list[tuple[float, dict]]:
        results: list[tuple[float, dict]] = []
        for kb_id in kb_ids:
            index = self._index_name(tenant_id, kb_id)
            exists = await self.client.indices.exists(index=index)
            if not exists:
                continue
            try:
                timer = RequestTimer()
                resp = await self.client.search(
                    index=index,
                    query={
                        "bool": {
                            "must": [{"match": {"text": {"query": query}}}],
                            "filter": [
                                {"term": {"tenant_id": tenant_id}},
                                {"term": {"kb_id": kb_id}},
                            ],
                        }
                    },
                    size=top_k,
                )
                hits = resp.get("hits", {}).get("hits", [])
                local_hits: list[dict] = []
                for h in hits:
                    score = h.get("_score", 0.0) or 0.0
                    src = h.get("_source", {})
                    record = src | {"chunk_id": h.get("_id"), "knowledge_base_id": kb_id}
                    results.append((score, record))
                    local_hits.append({"score": score, "knowledge_base_id": kb_id})
                metrics_collector.record_retrieval(
                    retriever="bm25_es",
                    query=query,
                    results=local_hits,
                    latency_ms=timer.get_metrics()["total_ms"],
                    backend="es",
                )
            except Exception as exc:
                logger.warning(f"ES search failed for kb {kb_id}: {exc}")
                metrics_collector.record_retrieval(
                    retriever="bm25_es",
                    query=query,
                    results=[],
                    latency_ms=0,
                    backend="es",
                    error=str(exc),
                )
        results.sort(key=lambda x: x[0], reverse=True)
        return results[:top_k]

    async def rebuild_from_db(self, **kwargs):
        # 重建由内存实现处理，ES 可直接依赖现有数据或重新索引
        return 0

    async def rebuild_all(self, **kwargs):
        return 0
