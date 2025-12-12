"""
LlamaIndex BM25 检索器

使用 LlamaIndex 封装的 BM25 检索，从数据库加载 chunks 构建内存索引。
使用全局缓存避免跨请求重复加载数据库。
"""

from llama_index.retrievers.bm25 import BM25Retriever as LlamaIndexBM25Retriever

from app.infra.bm25_cache import get_bm25_cache
from app.infra.llamaindex import nodes_from_chunks
from app.pipeline.base import BaseRetrieverOperator
from app.pipeline.registry import register_operator


@register_operator("retriever", "llama_bm25")
class LlamaBM25Retriever(BaseRetrieverOperator):
    """
    LlamaIndex BM25 检索器
    
    工作流程：
    1. 从全局缓存获取 chunks（命中）或从数据库加载（未命中）
    2. 转换为 LlamaIndex TextNode
    3. 构建 BM25 索引并检索
    
    缓存策略：
    - 全局单例缓存，跨请求共享
    - TTL 自动过期（默认 60 秒）
    - 文档更新时可手动失效
    """
    name = "llama_bm25"
    kind = "retriever"

    def __init__(self, top_k: int = 5, max_chunks: int = 5000, cache_ttl: int = 60):
        self.default_top_k = top_k
        self.max_chunks = max_chunks
        self.cache_ttl = cache_ttl

    async def retrieve(
        self,
        *,
        query: str,
        tenant_id: str,
        kb_ids: list[str],
        top_k: int,
    ):
        # 从全局缓存获取 chunks
        cache = get_bm25_cache(ttl=self.cache_ttl)
        chunks = await cache.get(tenant_id, kb_ids)
        
        if chunks is None:
            # 缓存未命中，从数据库加载
            from app.services.query import collect_chunks_for_kbs
            chunks = await collect_chunks_for_kbs(tenant_id=tenant_id, kb_ids=kb_ids, limit=self.max_chunks)
            await cache.set(tenant_id, kb_ids, chunks, ttl=self.cache_ttl)
        
        if not chunks:
            return []
        
        # 转换为 LlamaIndex 节点
        nodes = nodes_from_chunks(chunks=chunks)
        
        # 构建 BM25 检索器并执行检索
        retriever = LlamaIndexBM25Retriever.from_defaults(nodes=nodes, similarity_top_k=top_k or self.default_top_k)
        
        raw_results = list(retriever.retrieve(query))
        
        # Min-Max 归一化到 0-1 范围，确保与向量检索分数尺度一致
        if raw_results:
            raw_scores = [n.score or 0.0 for n in raw_results]
            min_score = min(raw_scores)
            max_score = max(raw_scores)
            score_range = max_score - min_score
            
            def normalize(s: float) -> float:
                if score_range == 0:
                    return 1.0 if max_score > 0 else 0.0
                return (s - min_score) / score_range
        else:
            normalize = lambda s: s
        
        results = []
        for node in raw_results:
            meta = node.metadata or {}
            results.append(
                {
                    "chunk_id": node.node_id,
                    "text": node.text,
                    "score": normalize(node.score or 0.0),
                    "metadata": meta,
                    "knowledge_base_id": meta.get("knowledge_base_id") or meta.get("kb_id"),
                    "document_id": meta.get("document_id"),
                    "source": "bm25",
                }
            )
        return results
