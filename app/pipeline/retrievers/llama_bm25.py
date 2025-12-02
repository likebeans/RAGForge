"""
LlamaIndex BM25 检索器

使用 LlamaIndex 封装的 BM25 检索，从数据库加载 chunks 构建内存索引。
为避免重复构建，加入简单的内存缓存（按租户+KB 集合 + TTL）。
"""

import time

from llama_index.retrievers.bm25 import BM25Retriever as LlamaIndexBM25Retriever

from app.infra.llamaindex import nodes_from_chunks
from app.pipeline.base import BaseRetrieverOperator
from app.pipeline.registry import register_operator
# 延迟导入以避免循环依赖，在函数内部导入 collect_chunks_for_kbs


@register_operator("retriever", "llama_bm25")
class LlamaBM25Retriever(BaseRetrieverOperator):
    """
    LlamaIndex BM25 检索器
    
    工作流程：
    1. 从数据库加载指定知识库的所有 chunks
    2. 转换为 LlamaIndex TextNode
    3. 构建内存 BM25 索引并检索
    
    注意：每次检索都会重建索引，适合小规模数据
    """
    name = "llama_bm25"
    kind = "retriever"

    def __init__(self, top_k: int = 5, max_chunks: int = 5000, cache_ttl: int = 60):
        self.default_top_k = top_k
        self.max_chunks = max_chunks
        self.cache_ttl = cache_ttl
        self._cache: dict[tuple, tuple[float, list[dict]]] = {}  # key -> (ts, chunks)

    async def retrieve(
        self,
        *,
        query: str,
        tenant_id: str,
        kb_ids: list[str],
        top_k: int,
    ):
        # 从数据库加载 chunks
        chunks = await self._get_chunks_cached(tenant_id=tenant_id, kb_ids=kb_ids)
        
        # 转换为 LlamaIndex 节点
        nodes = nodes_from_chunks(chunks=chunks)
        
        # 构建 BM25 检索器并执行检索
        retriever = LlamaIndexBM25Retriever.from_defaults(nodes=nodes, similarity_top_k=top_k or self.default_top_k)
        
        results = []
        for node in retriever.retrieve(query):
            meta = node.metadata or {}
            results.append(
                {
                    "chunk_id": node.node_id,
                    "text": node.text,
                    "score": node.score or 0.0,
                    "metadata": meta,
                    "knowledge_base_id": meta.get("knowledge_base_id") or meta.get("kb_id"),
                    "document_id": meta.get("document_id"),
                    "source": "bm25",
                }
            )
        return results

    async def _get_chunks_cached(self, tenant_id: str, kb_ids: list[str]) -> list[dict]:
        key = (tenant_id, tuple(sorted(kb_ids)))
        now = time.time()
        ts_chunks = self._cache.get(key)
        if ts_chunks and now - ts_chunks[0] < self.cache_ttl:
            return ts_chunks[1]

        # 延迟导入以避免循环依赖
        from app.services.query import collect_chunks_for_kbs
        chunks = await collect_chunks_for_kbs(tenant_id=tenant_id, kb_ids=kb_ids, limit=self.max_chunks)
        self._cache[key] = (now, chunks)
        return chunks
