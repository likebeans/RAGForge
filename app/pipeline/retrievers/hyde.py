"""
HyDE 检索器

将 HyDE 查询变换与检索器结合，用假设性答案进行检索后合并结果。

特性：
- 封装任意检索器
- 多查询检索后 RRF 融合
- 可选条件触发
- LLM 失败时优雅回退
"""

import logging
from typing import Any, TYPE_CHECKING

from app.pipeline.base import BaseRetrieverOperator
from app.pipeline.registry import register_operator
from app.pipeline.query_transforms.hyde import (
    HyDEQueryTransform,
    HyDEConfig,
    get_hyde_transform,
)

if TYPE_CHECKING:
    from app.pipeline import operator_registry

logger = logging.getLogger(__name__)


@register_operator("retriever", "hyde")
class HyDERetriever(BaseRetrieverOperator):
    """
    HyDE 检索器
    
    使用 HyDE 生成假设性答案，分别检索后用 RRF 融合结果。
    
    使用示例：
    ```python
    retriever = HyDERetriever(
        base_retriever="dense",
        hyde_config=HyDEConfig(num_queries=4),
    )
    results = await retriever.retrieve(query="什么是RAG？", ...)
    ```
    """
    
    name = "hyde"
    kind = "retriever"
    
    def __init__(
        self,
        base_retriever: str = "dense",
        base_retriever_params: dict | None = None,
        hyde_config: HyDEConfig | None = None,
        rrf_k: int = 60,
        num_queries: int | None = None,
        include_original: bool | None = None,
        **kwargs,  # 忽略前端传来的未知参数
    ):
        """
        Args:
            base_retriever: 底层检索器名称
            base_retriever_params: 底层检索器参数
            hyde_config: HyDE 配置
            rrf_k: RRF 融合常数
            num_queries: 生成假设答案数量（快捷参数，会覆盖 hyde_config）
            include_original: 是否保留原始查询（快捷参数，会覆盖 hyde_config）
        """
        self.base_retriever_name = base_retriever
        self.base_retriever_params = base_retriever_params or {}
        self.rrf_k = rrf_k
        self._hyde_transform: HyDEQueryTransform | None = None
        
        # 支持直接传递参数，构造 hyde_config
        if hyde_config is not None:
            self.hyde_config = hyde_config
        elif num_queries is not None or include_original is not None:
            self.hyde_config = HyDEConfig(
                num_queries=num_queries or 4,
                include_original=include_original if include_original is not None else True,
            )
        else:
            self.hyde_config = None
    
    def _get_base_retriever(self) -> BaseRetrieverOperator:
        """获取底层检索器"""
        # 延迟导入避免循环导入
        from app.pipeline import operator_registry
        
        factory = operator_registry.get("retriever", self.base_retriever_name)
        if not factory:
            raise ValueError(f"未找到检索器: {self.base_retriever_name}")
        return factory(**self.base_retriever_params)
    
    def _get_hyde_transform(self) -> HyDEQueryTransform | None:
        """延迟初始化 HyDE 变换器"""
        if self._hyde_transform is None:
            self._hyde_transform = get_hyde_transform(self.hyde_config)
        return self._hyde_transform
    
    async def retrieve(
        self,
        *,
        query: str,
        tenant_id: str,
        kb_ids: list[str],
        top_k: int,
    ) -> list[dict[str, Any]]:
        """
        执行 HyDE 检索
        
        1. 生成假设性答案
        2. 用每个假设答案检索
        3. RRF 融合结果
        """
        base_retriever = self._get_base_retriever()
        hyde_transform = self._get_hyde_transform()
        
        # 如果 HyDE 不可用，直接使用底层检索器
        if hyde_transform is None:
            logger.warning("HyDE 未启用或不可用，使用底层检索器（hyde_queries=[original]）")
            base_hits = await base_retriever.retrieve(
                query=query,
                tenant_id=tenant_id,
                kb_ids=kb_ids,
                top_k=top_k,
            )
            for hit in base_hits:
                hit["source"] = "hyde_fallback"
                hit["hyde_queries"] = [query]
                hit["hyde_queries_count"] = 1
            return base_hits
        
        # 生成假设性答案
        try:
            queries = await hyde_transform.agenerate(query)
            logger.info(f"HyDE 生成 {len(queries)} 个查询")
        except Exception as e:
            logger.warning(f"HyDE 生成失败，回退到原始查询: {e}")
            queries = [query]
        else:
            logger.info(f"HyDE 查询集: {queries}")
        
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
        
        # 标记来源
        for hit in fused:
            hit["source"] = "hyde"
            hit["hyde_queries_count"] = len(queries)
            hit["hyde_queries"] = queries
        
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
