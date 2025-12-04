"""
RAPTOR Retriever

基于 RAPTOR 索引的检索器，支持多层次摘要树检索。

检索模式：
- collapsed: 扁平化检索，所有层级节点一起 top-k
- tree_traversal: 树遍历检索，从顶层向下逐层筛选

注意：RAPTOR 检索需要先通过 ingestion 服务使用 raptor indexer 构建索引。
"""

import logging
from typing import Any

from app.pipeline.base import BaseRetrieverOperator
from app.pipeline.registry import register_operator, operator_registry

logger = logging.getLogger(__name__)

# 尝试导入 RAPTOR 依赖
try:
    from app.pipeline.indexers.raptor import (
        RaptorIndexer, 
        create_raptor_indexer_from_config,
        RAPTOR_AVAILABLE,
    )
except ImportError:
    RAPTOR_AVAILABLE = False


@register_operator("retriever", "raptor")
class RaptorRetriever(BaseRetrieverOperator):
    """
    RAPTOR 检索器
    
    基于 RAPTOR 索引进行多层次检索。
    
    参数：
    - mode: 检索模式，"collapsed" 或 "tree_traversal"
    - base_retriever: 当 RAPTOR 索引不可用时的回退检索器
    
    使用方式：
    1. 知识库配置中启用 raptor indexer
    2. 检索时使用 raptor retriever
    
    示例配置：
    ```json
    {
        "ingestion": {
            "indexer": {"name": "raptor", "params": {"max_layers": 3}}
        },
        "query": {
            "retriever": {"name": "raptor", "params": {"mode": "collapsed"}}
        }
    }
    ```
    """
    
    name = "raptor"
    kind = "retriever"
    
    def __init__(
        self,
        mode: str = "collapsed",
        base_retriever: str = "dense",
        top_k: int = 5,
    ):
        """
        初始化 RAPTOR 检索器
        
        Args:
            mode: 检索模式
                - "collapsed": 扁平化检索（默认，速度快）
                - "tree_traversal": 树遍历检索（更精确但较慢）
            base_retriever: 回退检索器名称
            top_k: 默认返回数量
        """
        self.mode = mode
        self.base_retriever_name = base_retriever
        self.top_k = top_k
        
        # 延迟初始化
        self._indexer: RaptorIndexer | None = None
        self._base_retriever: Any = None
    
    def _get_base_retriever(self) -> Any:
        """获取回退检索器"""
        if self._base_retriever is None:
            factory = operator_registry.get("retriever", self.base_retriever_name)
            if factory:
                self._base_retriever = factory()
            else:
                # 使用 dense 检索器作为默认
                from app.pipeline.retrievers.dense import DenseRetriever
                self._base_retriever = DenseRetriever()
        return self._base_retriever
    
    async def retrieve(
        self,
        *,
        query: str,
        tenant_id: str,
        kb_ids: list[str],
        top_k: int = 5,
        **kwargs: Any,
    ) -> list[dict]:
        """
        执行检索
        
        RAPTOR 检索器目前回退到 base_retriever，
        因为 RAPTOR 索引需要在摄取阶段构建。
        
        完整的 RAPTOR 支持需要：
        1. 知识库配置 raptor indexer
        2. 摄取时自动构建 RAPTOR 树
        3. 检索时加载对应的 RAPTOR 索引
        
        Args:
            query: 查询文本
            tenant_id: 租户 ID
            kb_ids: 知识库 ID 列表
            top_k: 返回数量
            
        Returns:
            检索结果列表
        """
        if not RAPTOR_AVAILABLE:
            logger.warning("RAPTOR 不可用，回退到 %s 检索器", self.base_retriever_name)
            return await self._fallback_retrieve(
                query=query,
                tenant_id=tenant_id,
                kb_ids=kb_ids,
                top_k=top_k,
                **kwargs,
            )
        
        # TODO: 从 KB 配置加载 RAPTOR 索引
        # 当前版本回退到 base_retriever
        # 未来版本将支持：
        # 1. 检查 KB 是否启用了 RAPTOR indexer
        # 2. 加载对应的 RAPTOR 索引
        # 3. 使用 RAPTOR retriever 进行检索
        
        logger.info(
            "RAPTOR 检索 (mode=%s) - 当前版本回退到 %s",
            self.mode,
            self.base_retriever_name,
        )
        
        results = await self._fallback_retrieve(
            query=query,
            tenant_id=tenant_id,
            kb_ids=kb_ids,
            top_k=top_k,
            **kwargs,
        )
        
        # 添加 raptor 标记
        for r in results:
            r["raptor_mode"] = self.mode
            r["raptor_fallback"] = True
        
        return results
    
    async def _fallback_retrieve(
        self,
        query: str,
        tenant_id: str,
        kb_ids: list[str],
        top_k: int,
        **kwargs: Any,
    ) -> list[dict]:
        """使用回退检索器"""
        base = self._get_base_retriever()
        return await base.retrieve(
            query=query,
            tenant_id=tenant_id,
            kb_ids=kb_ids,
            top_k=top_k,
            **kwargs,
        )
