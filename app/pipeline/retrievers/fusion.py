"""
融合检索器（RRF + Rerank）

支持多种融合策略：
- weighted: 加权融合（默认）
- rrf: Reciprocal Rank Fusion
- 可选 Rerank 精排
"""

from typing import Literal

from app.pipeline.base import BaseRetrieverOperator
from app.pipeline.registry import operator_registry, register_operator


def reciprocal_rank_fusion(
    ranked_lists: list[list[dict]],
    k: int = 60,
) -> list[dict]:
    """
    RRF (Reciprocal Rank Fusion) 融合算法
    
    公式: score = sum(1 / (k + rank_i)) for each list
    
    Args:
        ranked_lists: 多个排序后的结果列表
        k: RRF 常数，默认 60（论文推荐值）
    
    Returns:
        融合后按分数降序排列的结果
    """
    fused_scores: dict[str, float] = {}
    doc_map: dict[str, dict] = {}
    
    for ranked_list in ranked_lists:
        for rank, doc in enumerate(ranked_list, start=1):
            doc_id = doc["chunk_id"]
            # 累加 RRF 分数
            fused_scores[doc_id] = fused_scores.get(doc_id, 0.0) + 1.0 / (k + rank)
            # 保留文档信息（取第一次出现的）
            if doc_id not in doc_map:
                doc_map[doc_id] = doc.copy()
    
    # 更新分数并排序
    for doc_id, score in fused_scores.items():
        doc_map[doc_id]["score"] = score
        doc_map[doc_id]["source"] = "rrf"
    
    return sorted(doc_map.values(), key=lambda x: x.get("score", 0.0), reverse=True)


def weighted_fusion(
    ranked_lists: list[list[dict]],
    weights: list[float],
) -> list[dict]:
    """
    加权融合算法
    
    Args:
        ranked_lists: 多个排序后的结果列表
        weights: 每个列表的权重
    
    Returns:
        融合后按分数降序排列的结果
    """
    fused_scores: dict[str, float] = {}
    doc_map: dict[str, dict] = {}
    
    for weight, ranked_list in zip(weights, ranked_lists):
        for doc in ranked_list:
            doc_id = doc["chunk_id"]
            score = doc.get("score", 0.0) * weight
            fused_scores[doc_id] = fused_scores.get(doc_id, 0.0) + score
            if doc_id not in doc_map:
                doc_map[doc_id] = doc.copy()
    
    for doc_id, score in fused_scores.items():
        doc_map[doc_id]["score"] = score
        doc_map[doc_id]["source"] = "weighted"
    
    return sorted(doc_map.values(), key=lambda x: x.get("score", 0.0), reverse=True)


@register_operator("retriever", "fusion")
class FusionRetriever(BaseRetrieverOperator):
    """
    融合检索器
    
    功能：
    1. 结合 Dense 和 BM25 检索
    2. 支持 RRF 或加权融合
    3. 可选 Rerank 精排
    
    使用示例：
    ```python
    retriever = operator_registry.get("retriever", "fusion")(
        mode="rrf",
        rerank=True,
        rerank_model="BAAI/bge-reranker-base",
        rerank_top_n=10,
    )
    ```
    """
    name = "fusion"
    kind = "retriever"

    def __init__(
        self,
        mode: Literal["weighted", "rrf"] = "rrf",
        dense_weight: float = 0.7,
        bm25_weight: float = 0.3,
        rrf_k: int = 60,
        rerank: bool = False,
        rerank_model: str = "BAAI/bge-reranker-base",
        rerank_top_n: int = 10,
        top_k: int = 20,
        embedding_config: dict | None = None,
        **kwargs,  # 忽略前端传来的未知参数（如 method）
    ):
        """
        Args:
            mode: 融合模式，"weighted" 或 "rrf"
            dense_weight: 稠密检索权重（仅 weighted 模式）
            bm25_weight: BM25 检索权重（仅 weighted 模式）
            rrf_k: RRF 常数（仅 rrf 模式）
            rerank: 是否启用 Rerank
            rerank_model: Rerank 模型名称
            rerank_top_n: Rerank 后返回的结果数
            top_k: 默认召回数量
            embedding_config: 可选的 embedding 配置（来自知识库配置）
        """
        self.mode = mode
        self.dense_weight = dense_weight
        self.bm25_weight = bm25_weight
        self.rrf_k = rrf_k
        self.rerank_enabled = rerank
        self.rerank_top_n = rerank_top_n
        self.default_top_k = top_k
        self.embedding_config = embedding_config
        
        # 延迟初始化子检索器
        self._dense = None
        self._bm25 = None

    def _get_dense(self):
        if self._dense is None:
            self._dense = operator_registry.get("retriever", "llama_dense")(
                embedding_config=self.embedding_config
            )
        return self._dense

    def _get_bm25(self):
        if self._bm25 is None:
            self._bm25 = operator_registry.get("retriever", "llama_bm25")()
        return self._bm25

    async def retrieve(
        self,
        *,
        query: str,
        tenant_id: str,
        kb_ids: list[str],
        top_k: int,
    ):
        final_top_k = top_k or self.default_top_k
        # 召回阶段需要更多结果用于融合和 rerank
        recall_k = final_top_k * 3 if self.rerank_enabled else final_top_k * 2
        
        # 并行执行两种检索
        dense_hits = await self._get_dense().retrieve(
            query=query, tenant_id=tenant_id, kb_ids=kb_ids, top_k=recall_k
        )
        bm25_hits = await self._get_bm25().retrieve(
            query=query, tenant_id=tenant_id, kb_ids=kb_ids, top_k=recall_k
        )
        
        # 融合
        if self.mode == "rrf":
            fused = reciprocal_rank_fusion([dense_hits, bm25_hits], k=self.rrf_k)
        else:
            fused = weighted_fusion(
                [dense_hits, bm25_hits],
                [self.dense_weight, self.bm25_weight]
            )
        
        # Rerank（使用 infra.rerank 多提供商支持）
        if self.rerank_enabled:
            from app.infra.rerank import rerank_results
            
            # 取前 N 个进行 rerank（控制成本）
            candidates = fused[:min(len(fused), self.rerank_top_n * 3)]
            documents = [doc["text"] for doc in candidates]
            
            try:
                reranked = await rerank_results(
                    query=query,
                    documents=documents,
                    top_k=self.rerank_top_n,
                )
                
                # 更新分数并重排
                result = []
                for r in reranked:
                    idx = r["index"]
                    if idx < len(candidates):
                        doc = candidates[idx].copy()
                        doc["score"] = r["score"]
                        doc["source"] = "rerank"
                        result.append(doc)
                
                fused = result
            except Exception as e:
                import logging
                logging.warning(f"Rerank 失败，使用融合结果: {e}")
        
        return fused[:final_top_k]
