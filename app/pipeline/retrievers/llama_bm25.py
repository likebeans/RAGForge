"""
LlamaIndex BM25 检索器

使用 rank_bm25 + jieba 实现中文 BM25 检索。
从数据库加载 chunks 构建内存索引，使用全局缓存避免重复加载。

注意：LlamaIndex BM25Retriever 的 tokenizer 参数已废弃，
因此直接使用 rank_bm25 库实现中文分词支持。
"""

import jieba
from rank_bm25 import BM25Okapi

from app.infra.bm25_cache import get_bm25_cache
from app.pipeline.base import BaseRetrieverOperator
from app.pipeline.registry import register_operator


def _tokenize(text: str) -> list[str]:
    """中文分词：使用 jieba 搜索引擎模式"""
    return list(jieba.cut_for_search(text.lower()))


@register_operator("retriever", "llama_bm25")
class LlamaBM25Retriever(BaseRetrieverOperator):
    """
    BM25 检索器（带全局缓存）
    
    工作流程：
    1. 从全局缓存获取 chunks（命中）或从数据库加载（未命中）
    2. 使用 jieba 分词构建 BM25 索引
    3. 执行检索并归一化分数
    
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
        
        # 使用 jieba 分词构建 BM25 索引
        corpus = [_tokenize(ch["text"]) for ch in chunks]
        bm25 = BM25Okapi(corpus)
        
        # 执行检索
        query_tokens = _tokenize(query)
        scores = bm25.get_scores(query_tokens)
        
        # 按分数排序，取 top_k
        effective_top_k = top_k or self.default_top_k
        scored_chunks = sorted(
            zip(scores, chunks),
            key=lambda x: x[0],
            reverse=True
        )[:effective_top_k]
        
        # Min-Max 归一化到 0-1 范围
        if scored_chunks:
            raw_scores = [s for s, _ in scored_chunks]
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
        for score, chunk in scored_chunks:
            meta = chunk.get("metadata", {})
            results.append(
                {
                    "chunk_id": chunk["chunk_id"],
                    "text": chunk["text"],
                    "score": normalize(float(score)),
                    "metadata": meta,
                    "knowledge_base_id": meta.get("knowledge_base_id") or meta.get("kb_id"),
                    "document_id": meta.get("document_id"),
                    "source": "bm25",
                }
            )
        return results
