"""
多查询检索器（Multi-Query Retriever）

使用 RAG Fusion 策略生成多个查询变体，分别检索后 RRF 融合结果。
适用于提高召回覆盖率，尤其是用户查询表述不精确时。

特点：
- 自动生成多个查询变体
- 多路召回后 RRF 融合
- 可选任意底层检索器
"""

import logging
from typing import Any

from app.pipeline.base import BaseRetrieverOperator
from app.pipeline.registry import register_operator, operator_registry
from app.pipeline.query_transforms.rag_fusion import RAGFusionTransform, FusionConfig

logger = logging.getLogger(__name__)


@register_operator("retriever", "multi_query")
class MultiQueryRetriever(BaseRetrieverOperator):
    """
    多查询检索器
    
    使用示例：
    ```python
    retriever = operator_registry.get("retriever", "multi_query")(
        base_retriever="dense",
        num_queries=3,
    )
    results = await retriever.retrieve(query="什么是RAG？", ...)
    ```
    """
    
    name = "multi_query"
    kind = "retriever"
    
    def __init__(
        self,
        base_retriever: str = "dense",
        base_retriever_params: dict | None = None,
        num_queries: int = 3,
        include_original: bool = True,
        rrf_k: int = 60,
    ):
        """
        Args:
            base_retriever: 底层检索器名称
            base_retriever_params: 底层检索器参数
            num_queries: 生成的查询变体数量
            include_original: 是否保留原始查询
            rrf_k: RRF 融合常数
        """
        self.base_retriever_name = base_retriever
        self.base_retriever_params = base_retriever_params or {}
        self.num_queries = num_queries
        self.include_original = include_original
        self.rrf_k = rrf_k
        self._query_transform: RAGFusionTransform | None = None
    
    def _get_base_retriever(self) -> BaseRetrieverOperator:
        """获取底层检索器"""
        factory = operator_registry.get("retriever", self.base_retriever_name)
        if not factory:
            raise ValueError(f"未找到检索器: {self.base_retriever_name}")
        return factory(**self.base_retriever_params)
    
    def _get_query_transform(self) -> RAGFusionTransform | None:
        """延迟初始化查询变换器"""
        if self._query_transform is None:
            try:
                self._query_transform = RAGFusionTransform(
                    num_queries=self.num_queries,
                    include_original=self.include_original,
                )
            except Exception as e:
                logger.warning(f"初始化 RAGFusionTransform 失败: {e}")
                return None
        return self._query_transform
    
    async def retrieve(
        self,
        *,
        query: str,
        tenant_id: str,
        kb_ids: list[str],
        top_k: int,
    ) -> list[dict[str, Any]]:
        """
        执行多查询检索
        
        1. 生成多个查询变体
        2. 用每个查询检索
        3. RRF 融合结果
        """
        base_retriever = self._get_base_retriever()
        query_transform = self._get_query_transform()
        
        # 生成查询变体
        if query_transform is not None:
            try:
                queries = await query_transform.agenerate(query)
                logger.info(f"多查询扩展生成 {len(queries)} 个查询")
            except Exception as e:
                logger.warning(f"查询扩展失败，使用原始查询: {e}")
                queries = [query]
        else:
            queries = [query]
        
        # 用每个查询检索
        all_results: list[list[dict]] = []
        for q in queries:
            results = await base_retriever.retrieve(
                query=q,
                tenant_id=tenant_id,
                kb_ids=kb_ids,
                top_k=top_k,
            )
            all_results.append(results)
        
        # RRF 融合
        fused = self._rrf_fuse(all_results, top_k)
        
        # 构建每个查询的详细检索结果
        retrieval_details = [
            {
                "query": queries[i],
                "hits_count": len(all_results[i]),
                "hits": all_results[i],  # 完整的检索结果
            }
            for i in range(len(queries))
        ]
        
        # 标记来源和生成的查询
        for hit in fused:
            hit["source"] = "multi_query"
            hit["queries_count"] = len(queries)
            hit["generated_queries"] = queries
            hit["retrieval_details"] = retrieval_details  # 每个查询的完整检索结果
        
        return fused
    
    def _rrf_fuse(
        self,
        result_lists: list[list[dict]],
        top_k: int,
    ) -> list[dict]:
        """RRF 融合多个结果列表"""
        scores: dict[str, float] = {}
        items: dict[str, dict] = {}
        
        for results in result_lists:
            for rank, hit in enumerate(results):
                chunk_id = hit["chunk_id"]
                rrf_score = 1.0 / (self.rrf_k + rank + 1)
                scores[chunk_id] = scores.get(chunk_id, 0) + rrf_score
                if chunk_id not in items:
                    items[chunk_id] = hit.copy()
        
        # 按 RRF 分数排序
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
        
        result = []
        for chunk_id in sorted_ids[:top_k]:
            hit = items[chunk_id]
            hit["rrf_score"] = scores[chunk_id]
            result.append(hit)
        
        return result
