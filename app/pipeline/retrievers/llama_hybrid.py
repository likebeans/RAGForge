"""
LlamaIndex 混合检索器

结合 LlamaIndex 的稠密检索和 BM25 检索，通过加权融合提升效果。
"""

from itertools import chain

from app.pipeline.base import BaseRetrieverOperator
from app.pipeline.registry import operator_registry, register_operator


@register_operator("retriever", "llama_hybrid")
class LlamaHybridRetriever(BaseRetrieverOperator):
    """
    LlamaIndex 混合检索器
    
    组合 llama_dense 和 llama_bm25 检索器，对结果进行加权融合。
    """
    name = "llama_hybrid"
    kind = "retriever"

    def __init__(self, dense_weight: float = 0.7, bm25_weight: float = 0.3, top_k: int = 5):
        """
        Args:
            dense_weight: 稠密检索权重
            bm25_weight: BM25 检索权重
            top_k: 默认返回结果数量
        """
        self.dense_weight = dense_weight
        self.bm25_weight = bm25_weight
        self.default_top_k = top_k
        self.dense = operator_registry.get("retriever", "llama_dense")()
        self.bm25 = operator_registry.get("retriever", "llama_bm25")()

    async def retrieve(
        self,
        *,
        query: str,
        tenant_id: str,
        kb_ids: list[str],
        top_k: int,
    ):
        # 执行两种检索
        dense_hits = await self.dense.retrieve(
            query=query, tenant_id=tenant_id, kb_ids=kb_ids, top_k=top_k or self.default_top_k
        )
        bm25_hits = await self.bm25.retrieve(
            query=query, tenant_id=tenant_id, kb_ids=kb_ids, top_k=top_k or self.default_top_k
        )

        # 加权融合
        merged: dict[str, dict] = {}
        for hit in chain(dense_hits, bm25_hits):
            cid = hit["chunk_id"]
            score = hit.get("score", 0.0)
            source = hit.get("source") or ("dense" if hit in dense_hits else "bm25")
            weight = self.dense_weight if source == "dense" else self.bm25_weight
            merged.setdefault(cid, hit)
            merged[cid]["score"] = merged.get(cid, {}).get("score", 0.0) + score * weight
            merged[cid]["source"] = source

        # 按分数排序
        sorted_hits = sorted(merged.values(), key=lambda x: x.get("score", 0.0), reverse=True)
        return sorted_hits[: top_k or self.default_top_k]
