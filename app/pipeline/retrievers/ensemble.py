"""
集成检索器（Ensemble Retriever）

支持任意组合多个检索器，使用 RRF 或加权融合。
比 fusion 更通用：可自由指定任意检索器组合。

特点：
- 灵活组合任意检索器
- 支持 RRF / 加权融合
- 可配置各检索器权重
- 支持并行执行
"""

import asyncio
import logging
from typing import Any, Literal

from app.pipeline.base import BaseRetrieverOperator
from app.pipeline.registry import register_operator, operator_registry

logger = logging.getLogger(__name__)


@register_operator("retriever", "ensemble")
class EnsembleRetriever(BaseRetrieverOperator):
    """
    集成检索器
    
    使用示例：
    ```python
    # 组合 dense + bm25 + hyde
    retriever = operator_registry.get("retriever", "ensemble")(
        retrievers=[
            {"name": "dense", "weight": 0.4},
            {"name": "bm25", "weight": 0.3},
            {"name": "hyde", "params": {"base_retriever": "dense"}, "weight": 0.3},
        ],
        mode="rrf",
    )
    results = await retriever.retrieve(query="问题", ...)
    ```
    """
    
    name = "ensemble"
    kind = "retriever"
    
    def __init__(
        self,
        retrievers: list[dict],
        mode: Literal["rrf", "weighted"] = "rrf",
        rrf_k: int = 60,
        parallel: bool = True,
    ):
        """
        Args:
            retrievers: 检索器配置列表，每个元素为 dict：
                - name: 检索器名称（必需）
                - params: 检索器参数（可选）
                - weight: 权重（可选，默认 1.0）
            mode: 融合模式，"rrf" 或 "weighted"
            rrf_k: RRF 常数（仅 rrf 模式）
            parallel: 是否并行执行检索
        """
        self.retriever_configs = retrievers
        self.mode = mode
        self.rrf_k = rrf_k
        self.parallel = parallel
        
        # 验证配置
        if not retrievers:
            raise ValueError("至少需要指定一个检索器")
        
        for cfg in retrievers:
            if "name" not in cfg:
                raise ValueError("每个检索器配置必须包含 'name' 字段")
        
        # 延迟初始化
        self._retrievers: list[tuple[BaseRetrieverOperator, float]] | None = None
    
    def _init_retrievers(self) -> list[tuple[BaseRetrieverOperator, float]]:
        """初始化所有子检索器"""
        if self._retrievers is not None:
            return self._retrievers
        
        self._retrievers = []
        for cfg in self.retriever_configs:
            name = cfg["name"]
            params = cfg.get("params", {})
            weight = cfg.get("weight", 1.0)
            
            factory = operator_registry.get("retriever", name)
            if not factory:
                raise ValueError(f"未找到检索器: {name}")
            
            retriever = factory(**params)
            self._retrievers.append((retriever, weight))
        
        return self._retrievers
    
    async def retrieve(
        self,
        *,
        query: str,
        tenant_id: str,
        kb_ids: list[str],
        top_k: int,
    ) -> list[dict[str, Any]]:
        """
        执行集成检索
        
        1. 并行/串行执行所有子检索器
        2. 使用 RRF 或加权融合结果
        """
        retrievers = self._init_retrievers()
        
        # 召回更多结果用于融合
        recall_k = top_k * 2
        
        # 执行检索
        if self.parallel:
            # 并行执行
            tasks = [
                retriever.retrieve(
                    query=query,
                    tenant_id=tenant_id,
                    kb_ids=kb_ids,
                    top_k=recall_k,
                )
                for retriever, _ in retrievers
            ]
            all_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 处理异常
            results_list = []
            for i, result in enumerate(all_results):
                if isinstance(result, Exception):
                    logger.warning(f"检索器 {self.retriever_configs[i]['name']} 执行失败: {result}")
                    results_list.append([])
                else:
                    results_list.append(result)
        else:
            # 串行执行
            results_list = []
            for retriever, _ in retrievers:
                try:
                    results = await retriever.retrieve(
                        query=query,
                        tenant_id=tenant_id,
                        kb_ids=kb_ids,
                        top_k=recall_k,
                    )
                    results_list.append(results)
                except Exception as e:
                    logger.warning(f"检索器执行失败: {e}")
                    results_list.append([])
        
        # 融合结果
        weights = [w for _, w in retrievers]
        
        if self.mode == "rrf":
            fused = self._rrf_fuse(results_list)
        else:
            fused = self._weighted_fuse(results_list, weights)
        
        # 标记来源
        for hit in fused[:top_k]:
            hit["source"] = "ensemble"
            hit["ensemble_mode"] = self.mode
        
        return fused[:top_k]
    
    def _rrf_fuse(self, results_list: list[list[dict]]) -> list[dict]:
        """RRF 融合"""
        scores: dict[str, float] = {}
        items: dict[str, dict] = {}
        
        for results in results_list:
            for rank, hit in enumerate(results):
                chunk_id = hit["chunk_id"]
                rrf_score = 1.0 / (self.rrf_k + rank + 1)
                scores[chunk_id] = scores.get(chunk_id, 0) + rrf_score
                if chunk_id not in items:
                    items[chunk_id] = hit.copy()
        
        # 更新分数并排序
        for chunk_id in items:
            items[chunk_id]["rrf_score"] = scores[chunk_id]
            items[chunk_id]["score"] = scores[chunk_id]
        
        return sorted(items.values(), key=lambda x: x.get("score", 0), reverse=True)
    
    def _weighted_fuse(
        self,
        results_list: list[list[dict]],
        weights: list[float],
    ) -> list[dict]:
        """加权融合"""
        scores: dict[str, float] = {}
        items: dict[str, dict] = {}
        
        # 归一化权重
        total_weight = sum(weights)
        normalized_weights = [w / total_weight for w in weights]
        
        for results, weight in zip(results_list, normalized_weights):
            for hit in results:
                chunk_id = hit["chunk_id"]
                score = hit.get("score", 0.0) * weight
                scores[chunk_id] = scores.get(chunk_id, 0) + score
                if chunk_id not in items:
                    items[chunk_id] = hit.copy()
        
        # 更新分数
        for chunk_id in items:
            items[chunk_id]["score"] = scores[chunk_id]
        
        return sorted(items.values(), key=lambda x: x.get("score", 0), reverse=True)
