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
        """
        self.mode = mode
        self.dense_weight = dense_weight
        self.bm25_weight = bm25_weight
        self.rrf_k = rrf_k
        self.rerank_enabled = rerank
        self.rerank_model = rerank_model
        self.rerank_top_n = rerank_top_n
        self.default_top_k = top_k
        
        # 延迟初始化子检索器
        self._dense = None
        self._bm25 = None
        self._reranker = None

    def _get_dense(self):
        if self._dense is None:
            self._dense = operator_registry.get("retriever", "llama_dense")()
        return self._dense

    def _get_bm25(self):
        if self._bm25 is None:
            self._bm25 = operator_registry.get("retriever", "llama_bm25")()
        return self._bm25

    def _get_reranker(self):
        if self._reranker is None and self.rerank_enabled:
            # 延迟导入以避免未安装时报错
            try:
                from llama_index.postprocessor.cohere_rerank import CohereRerank
            except ImportError:
                pass
            try:
                from sentence_transformers import CrossEncoder
                self._reranker = CrossEncoder(self.rerank_model)
            except ImportError:
                import logging
                logging.warning(
                    f"sentence-transformers 未安装，Rerank 功能不可用。"
                    f"请运行: uv add sentence-transformers"
                )
                self.rerank_enabled = False
        return self._reranker

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
        
        # Rerank
        if self.rerank_enabled:
            reranker = self._get_reranker()
            if reranker is not None:
                # 取前 N 个进行 rerank（控制成本）
                candidates = fused[:min(len(fused), self.rerank_top_n * 3)]
                
                # 构建 query-doc pairs
                pairs = [(query, doc["text"]) for doc in candidates]
                
                # 计算相关性分数
                scores = reranker.predict(pairs)
                
                # 更新分数并重排
                for doc, score in zip(candidates, scores):
                    doc["score"] = float(score)
                    doc["source"] = "rerank"
                
                fused = sorted(candidates, key=lambda x: x["score"], reverse=True)
        
        return fused[:final_top_k]
