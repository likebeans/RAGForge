"""
混合检索器

结合稠密向量检索和 BM25 稀疏检索的优势，通过加权融合提升检索效果。
适用于需要同时考虑语义相似性和关键词匹配的场景。
"""

from itertools import chain

from app.pipeline.base import BaseRetrieverOperator
from app.pipeline.registry import operator_registry, register_operator


@register_operator("retriever", "hybrid")
class HybridRetriever(BaseRetrieverOperator):
    """
    混合检索器
    
    工作流程：
    1. 分别执行 Dense 和 BM25 检索
    2. 对结果进行加权分数融合
    3. 去重并按融合分数排序
    
    权重配置建议：
    - 通用问答：dense_weight=0.7, sparse_weight=0.3
    - 精确查询：dense_weight=0.5, sparse_weight=0.5
    - 实体检索：dense_weight=0.3, sparse_weight=0.7
    """
    name = "hybrid"
    kind = "retriever"

    def __init__(
        self, 
        dense_weight: float = 0.7, 
        sparse_weight: float = 0.3,
        embedding_config: dict | None = None,
    ):
        """
        Args:
            dense_weight: 稠密检索结果的权重
            sparse_weight: 稀疏检索结果的权重
            embedding_config: 可选的 embedding 配置（来自知识库配置）
        """
        self.dense_weight = dense_weight
        self.sparse_weight = sparse_weight
        self.embedding_config = embedding_config
        self.dense = operator_registry.get("retriever", "dense")(embedding_config=embedding_config)
        self.bm25 = operator_registry.get("retriever", "bm25")()

    async def retrieve(
        self,
        *,
        query: str,
        tenant_id: str,
        kb_ids: list[str],
        top_k: int,
    ):
        # 并行执行两种检索
        dense_hits = await self.dense.retrieve(
            query=query, tenant_id=tenant_id, kb_ids=kb_ids, top_k=top_k
        )
        bm25_hits = await self.bm25.retrieve(
            query=query, tenant_id=tenant_id, kb_ids=kb_ids, top_k=top_k
        )
        
        # 加权融合：相同 chunk_id 的分数累加
        merged: dict[str, dict] = {}
        scores: dict[str, float] = {}  # 单独记录加权分数
        for hit in chain(dense_hits, bm25_hits):
            cid = hit["chunk_id"]
            score = hit.get("score", 0.0)
            source = hit.get("source") or ("dense" if hit in dense_hits else "bm25")
            weight = self.dense_weight if source == "dense" else self.sparse_weight
            if cid not in merged:
                merged[cid] = hit.copy()
                merged[cid]["source"] = source
            scores[cid] = scores.get(cid, 0.0) + score * weight
        
        # 更新融合分数
        for cid in merged:
            merged[cid]["score"] = scores[cid]
        
        # 按融合分数降序排序
        sorted_hits = sorted(merged.values(), key=lambda x: x.get("score", 0.0), reverse=True)
        return sorted_hits[:top_k]
