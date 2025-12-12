"""
BM25 稀疏检索器

基于 BM25 算法的关键词检索，擅长精确匹配。
适用于专业术语、实体名称等需要精确匹配的场景。

改进：从数据库加载 chunks 构建索引，支持容器重启后自动恢复。
"""

import time

from rank_bm25 import BM25Okapi

from app.pipeline.base import BaseRetrieverOperator
from app.pipeline.registry import register_operator


def _tokenize(text: str) -> list[str]:
    """
    简单分词：支持中英文
    
    - 英文按空格分割
    - 中文按字符分割（简单处理，生产环境建议用 jieba）
    """
    import re
    # 匹配英文单词或单个中文字符
    tokens = re.findall(r'[a-zA-Z0-9]+|[\u4e00-\u9fff]', text.lower())
    return tokens


@register_operator("retriever", "bm25")
class BM25Retriever(BaseRetrieverOperator):
    """
    BM25 检索器（从数据库加载）
    
    特点：
    - 基于词频统计（TF-IDF 变体）
    - 对关键词精确匹配效果好
    - 从数据库加载 chunks，支持持久化
    - 带缓存，避免重复加载
    """
    name = "bm25"
    kind = "retriever"

    def __init__(self, max_chunks: int = 5000, cache_ttl: int = 60):
        self.max_chunks = max_chunks
        self.cache_ttl = cache_ttl
        self._cache: dict[tuple, tuple[float, list[dict], BM25Okapi]] = {}  # key -> (ts, chunks, bm25)

    async def retrieve(
        self,
        *,
        query: str,
        tenant_id: str,
        kb_ids: list[str],
        top_k: int,
    ):
        # 从数据库加载 chunks 并构建 BM25 索引
        chunks, bm25 = await self._get_bm25_cached(tenant_id=tenant_id, kb_ids=kb_ids)
        
        if not chunks or bm25 is None:
            return []
        
        # BM25 检索
        query_tokens = _tokenize(query)
        scores = bm25.get_scores(query_tokens)
        
        # 按分数排序，取 top_k
        scored_chunks = sorted(
            zip(scores, chunks),
            key=lambda x: x[0],
            reverse=True
        )[:top_k]
        
        # Min-Max 归一化到 0-1 范围，确保与向量检索分数尺度一致
        if scored_chunks:
            raw_scores = [s for s, _ in scored_chunks]
            min_score = min(raw_scores)
            max_score = max(raw_scores)
            score_range = max_score - min_score
            
            # 归一化函数：避免除零，全部相同分数时归一化为 1.0
            def normalize(s: float) -> float:
                if score_range == 0:
                    return 1.0 if max_score > 0 else 0.0
                return (s - min_score) / score_range
        else:
            normalize = lambda s: s
        
        # 转换为统一的返回格式（不过滤零分，因为 BM25 分数可能很低但有意义）
        return [
            {
                "chunk_id": chunk["chunk_id"],
                "text": chunk["text"],
                "score": normalize(float(score)),
                "metadata": chunk.get("metadata", {}),
                "knowledge_base_id": chunk.get("metadata", {}).get("knowledge_base_id"),
                "document_id": chunk.get("metadata", {}).get("document_id"),
                "source": "bm25",
            }
            for score, chunk in scored_chunks
        ]

    async def _get_bm25_cached(self, tenant_id: str, kb_ids: list[str]) -> tuple[list[dict], BM25Okapi | None]:
        """获取缓存的 BM25 索引，过期则重新加载"""
        key = (tenant_id, tuple(sorted(kb_ids)))
        now = time.time()
        cached = self._cache.get(key)
        if cached and now - cached[0] < self.cache_ttl:
            return cached[1], cached[2]

        # 延迟导入以避免循环依赖
        from app.services.query import collect_chunks_for_kbs
        chunks = await collect_chunks_for_kbs(tenant_id=tenant_id, kb_ids=kb_ids, limit=self.max_chunks)
        
        if not chunks:
            return [], None
        
        # 构建 BM25 索引
        corpus = [_tokenize(ch["text"]) for ch in chunks]
        bm25 = BM25Okapi(corpus)
        
        self._cache[key] = (now, chunks, bm25)
        return chunks, bm25
