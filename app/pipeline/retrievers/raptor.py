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

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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


async def _get_raptor_nodes_for_kb(
    session: AsyncSession,
    tenant_id: str,
    kb_id: str,
) -> list[dict]:
    """
    从数据库加载知识库的 RAPTOR 节点
    
    Args:
        session: 数据库会话
        tenant_id: 租户 ID
        kb_id: 知识库 ID
        
    Returns:
        RAPTOR 节点列表，每个节点包含 id, text, level, metadata
    """
    from app.models.raptor_node import RaptorNode
    
    stmt = (
        select(RaptorNode)
        .where(RaptorNode.tenant_id == tenant_id)
        .where(RaptorNode.knowledge_base_id == kb_id)
        .where(RaptorNode.indexing_status == "indexed")
        .order_by(RaptorNode.level, RaptorNode.created_at)
    )
    
    result = await session.execute(stmt)
    db_nodes = result.scalars().all()
    
    nodes = []
    for node in db_nodes:
        nodes.append({
            "id": node.id,
            "text": node.text,
            "level": node.level,
            "chunk_id": node.chunk_id,
            "vector_id": node.vector_id,
            "metadata": node.extra_metadata or {},
        })
    
    return nodes


async def _check_raptor_index_exists(
    session: AsyncSession,
    tenant_id: str,
    kb_id: str,
) -> bool:
    """检查知识库是否有 RAPTOR 索引"""
    from app.models.raptor_node import RaptorNode
    from sqlalchemy import func
    
    stmt = (
        select(func.count(RaptorNode.id))
        .where(RaptorNode.tenant_id == tenant_id)
        .where(RaptorNode.knowledge_base_id == kb_id)
    )
    
    result = await session.execute(stmt)
    count = result.scalar() or 0
    
    return count > 0


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
        embedding_config: dict | None = None,
    ):
        """
        初始化 RAPTOR 检索器
        
        Args:
            mode: 检索模式
                - "collapsed": 扁平化检索（默认，速度快）
                - "tree_traversal": 树遍历检索（更精确但较慢）
            base_retriever: 回退检索器名称
            top_k: 默认返回数量
            embedding_config: 动态 embedding 配置（来自知识库配置）
        """
        self.mode = mode
        self.base_retriever_name = base_retriever
        self.top_k = top_k
        self.embedding_config = embedding_config
        
        # 延迟初始化
        self._indexer: RaptorIndexer | None = None
        self._base_retriever: Any = None
    
    def _get_base_retriever(self) -> Any:
        """获取回退检索器"""
        if self._base_retriever is None:
            factory = operator_registry.get("retriever", self.base_retriever_name)
            if factory:
                # 传递 embedding_config 给底层检索器
                try:
                    self._base_retriever = factory(embedding_config=self.embedding_config)
                except TypeError:
                    # 某些检索器可能不接受 embedding_config
                    self._base_retriever = factory()
            else:
                # 使用 dense 检索器作为默认
                from app.pipeline.retrievers.dense import DenseRetriever
                self._base_retriever = DenseRetriever(embedding_config=self.embedding_config)
        return self._base_retriever
    
    async def retrieve(
        self,
        *,
        query: str,
        tenant_id: str,
        kb_ids: list[str],
        top_k: int = 5,
        session: AsyncSession | None = None,
        **kwargs: Any,
    ) -> list[dict]:
        """
        执行 RAPTOR 检索
        
        检索流程：
        1. 检查是否有 RAPTOR 索引（需要传入 session）
        2. 如果有索引，对 RAPTOR 节点进行向量检索
        3. 如果没有索引，回退到 base_retriever
        
        Args:
            query: 查询文本
            tenant_id: 租户 ID
            kb_ids: 知识库 ID 列表
            top_k: 返回数量
            session: 数据库会话（用于检查 RAPTOR 索引）
            
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
        
        # 检查是否有 RAPTOR 索引
        has_raptor_index = False
        raptor_node_counts = {}
        if session:
            for kb_id in kb_ids:
                count = await self._get_raptor_node_count(session, tenant_id, kb_id)
                if count > 0:
                    has_raptor_index = True
                    raptor_node_counts[kb_id] = count
        
        if raptor_node_counts:
            logger.info(
                "[RAPTOR] 检测到索引: %s",
                {kb: f"{cnt}节点" for kb, cnt in raptor_node_counts.items()}
            )
        
        if not has_raptor_index:
            logger.info(
                "知识库没有 RAPTOR 索引，回退到 %s 检索器",
                self.base_retriever_name,
            )
            results = await self._fallback_retrieve(
                query=query,
                tenant_id=tenant_id,
                kb_ids=kb_ids,
                top_k=top_k,
                **kwargs,
            )
            for r in results:
                r["raptor_mode"] = self.mode
                r["raptor_fallback"] = True
            return results
        
        # 有 RAPTOR 索引，执行 RAPTOR 检索
        logger.info(
            "[RAPTOR] 开始检索 (mode=%s, top_k=%d, kb_ids=%s)",
            self.mode,
            top_k,
            kb_ids,
        )
        logger.info("[RAPTOR] Step 1: 查询向量化...")
        
        # 使用 base_retriever 进行向量检索（RAPTOR 节点已在向量库中）
        # TODO: 实现 tree_traversal 模式的分层检索
        import time
        start_time = time.time()
        
        logger.info("[RAPTOR] Step 2: 向量库检索 (使用 %s)...", self.base_retriever_name)
        results = await self._fallback_retrieve(
            query=query,
            tenant_id=tenant_id,
            kb_ids=kb_ids,
            top_k=top_k,
            **kwargs,
        )
        vector_time = time.time() - start_time
        logger.info("[RAPTOR] Step 2 完成: 检索到 %d 条结果 (耗时 %.1fms)", len(results), vector_time * 1000)
        
        # 如果有 session，尝试加载 RAPTOR 节点信息增强结果
        if session:
            logger.info("[RAPTOR] Step 3: 加载节点层级信息...")
            enrich_start = time.time()
            results = await self._enrich_with_raptor_info(
                session=session,
                tenant_id=tenant_id,
                kb_ids=kb_ids,
                results=results,
            )
            enrich_time = time.time() - enrich_start
            
            # 统计各层级节点分布
            level_stats = {}
            for r in results:
                level = r.get("raptor_level", 0)
                level_stats[level] = level_stats.get(level, 0) + 1
            
            logger.info(
                "[RAPTOR] Step 3 完成: 层级分布 %s (耗时 %.1fms)",
                {f"L{k}": v for k, v in sorted(level_stats.items())},
                enrich_time * 1000
            )
        
        # 添加 raptor 标记
        for r in results:
            r["raptor_mode"] = self.mode
            r["raptor_fallback"] = False
        
        total_time = time.time() - start_time
        logger.info(
            "[RAPTOR] 检索完成: %d 结果, 总耗时 %.1fms",
            len(results),
            total_time * 1000
        )
        
        return results
    
    async def _enrich_with_raptor_info(
        self,
        session: AsyncSession,
        tenant_id: str,
        kb_ids: list[str],
        results: list[dict],
    ) -> list[dict]:
        """
        用 RAPTOR 节点信息增强检索结果
        
        查找每个结果对应的 RAPTOR 节点，添加层级信息
        """
        from app.models.raptor_node import RaptorNode
        
        # 收集所有 chunk_id
        chunk_ids = [r.get("chunk_id") for r in results if r.get("chunk_id")]
        if not chunk_ids:
            return results
        
        # 查询对应的 RAPTOR 节点
        stmt = (
            select(RaptorNode)
            .where(RaptorNode.tenant_id == tenant_id)
            .where(RaptorNode.knowledge_base_id.in_(kb_ids))
            .where(RaptorNode.chunk_id.in_(chunk_ids))
        )
        
        result = await session.execute(stmt)
        raptor_nodes = {node.chunk_id: node for node in result.scalars().all()}
        
        # 增强结果
        for r in results:
            chunk_id = r.get("chunk_id")
            if chunk_id and chunk_id in raptor_nodes:
                node = raptor_nodes[chunk_id]
                r["raptor_level"] = node.level
                r["raptor_node_id"] = node.id
            else:
                r["raptor_level"] = 0  # 默认为叶子节点
        
        return results
    
    async def _get_raptor_node_count(
        self,
        session: AsyncSession,
        tenant_id: str,
        kb_id: str,
    ) -> int:
        """获取知识库的 RAPTOR 节点数量"""
        from app.models.raptor_node import RaptorNode
        from sqlalchemy import func
        
        stmt = (
            select(func.count(RaptorNode.id))
            .where(RaptorNode.tenant_id == tenant_id)
            .where(RaptorNode.knowledge_base_id == kb_id)
        )
        
        result = await session.execute(stmt)
        return result.scalar() or 0
    
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
