"""
RAPTOR Retriever

基于 RAPTOR 索引的检索器，支持多层次摘要树检索。

检索模式：
- collapsed: 扁平化检索，所有层级节点一起 top-k
- tree_traversal: 树遍历检索，从顶层向下逐层筛选

注意：RAPTOR 检索需要先通过 ingestion 服务使用 raptor indexer 构建索引。
"""

import logging
import time
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.pipeline.base import BaseRetrieverOperator
from app.pipeline.registry import register_operator, operator_registry

logger = logging.getLogger(__name__)

# 尝试导入 RAPTOR 依赖
try:
    from app.pipeline.indexers.raptor import (
        RaptorNativeIndexer as RaptorIndexer, 
        create_raptor_native_indexer_from_config as create_raptor_indexer_from_config,
        RAPTOR_NATIVE_AVAILABLE as RAPTOR_AVAILABLE,
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
        expand_to_leaves: bool = True,
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
            expand_to_leaves: 是否将摘要节点展开为原始 chunks（默认 True）
        """
        self.mode = mode
        self.base_retriever_name = base_retriever
        self.top_k = top_k
        self.embedding_config = embedding_config
        self.expand_to_leaves = expand_to_leaves
        
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
        
        start_time = time.time()
        
        # 根据模式选择检索策略
        if self.mode == "tree_traversal":
            # tree_traversal 模式需要 session 来加载 RAPTOR 树
            if not session:
                # 如果没有传入 session，创建一个新的
                from app.infra.db import async_session_factory
                async with async_session_factory() as new_session:
                    logger.info("[RAPTOR] 使用 tree_traversal 模式检索（新建 session）...")
                    results = await self._tree_traversal_retrieve(
                        query=query,
                        tenant_id=tenant_id,
                        kb_ids=kb_ids,
                        top_k=top_k,
                        session=new_session,
                        **kwargs,
                    )
            else:
                # tree_traversal 模式：从顶层向下逐层筛选
                logger.info("[RAPTOR] 使用 tree_traversal 模式检索...")
                results = await self._tree_traversal_retrieve(
                    query=query,
                    tenant_id=tenant_id,
                    kb_ids=kb_ids,
                    top_k=top_k,
                    session=session,
                    **kwargs,
                )
        else:
            # collapsed 模式：扁平化检索
            logger.info("[RAPTOR] Step 1: 查询向量化...")
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
        
        # 如果启用了展开功能，将摘要节点展开为原始 chunks
        if self.expand_to_leaves and session:
            results = await self._expand_summary_to_leaves(
                session=session,
                tenant_id=tenant_id,
                kb_ids=kb_ids,
                results=results,
            )
        
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
    
    async def _load_raptor_tree(
        self,
        session: AsyncSession,
        tenant_id: str,
        kb_ids: list[str],
    ) -> dict[str, dict]:
        """
        从数据库加载 RAPTOR 节点树结构
        
        Returns:
            节点字典，key 为节点 ID，value 为节点信息
        """
        from app.models.raptor_node import RaptorNode
        
        # 只查询已完成索引的节点
        # 注意：原生 RAPTOR 实现会正确设置 indexing_status="indexed"
        # 如果使用旧的 LlamaIndex 实现，节点可能是 pending 状态，需要重新构建索引
        stmt = (
            select(RaptorNode)
            .where(RaptorNode.tenant_id == tenant_id)
            .where(RaptorNode.knowledge_base_id.in_(kb_ids))
            .where(RaptorNode.indexing_status == "indexed")
        )
        
        result = await session.execute(stmt)
        db_nodes = result.scalars().all()
        
        nodes = {}
        for node in db_nodes:
            nodes[node.id] = {
                "id": node.id,
                "text": node.text,
                "level": node.level,
                "chunk_id": node.chunk_id,
                "parent_id": node.parent_id,
                "children_ids": node.children_ids or [],
                "vector_id": node.vector_id,
                "metadata": node.extra_metadata or {},
            }
        
        return nodes
    
    async def _find_leaf_nodes(
        self,
        node_id: str,
        nodes: dict[str, dict],
        visited: set[str] | None = None,
    ) -> list[dict]:
        """
        递归查找节点的所有叶子节点（level=0 的原始 chunks）
        
        Args:
            node_id: 起始节点 ID
            nodes: 节点字典
            visited: 已访问节点集合（防止循环）
            
        Returns:
            叶子节点列表
        """
        if visited is None:
            visited = set()
        
        if node_id in visited:
            return []
        visited.add(node_id)
        
        node = nodes.get(node_id)
        if not node:
            return []
        
        # 如果是叶子节点，直接返回
        if node["level"] == 0:
            return [node]
        
        # 递归查找子节点
        leaf_nodes = []
        for child_id in node.get("children_ids", []):
            leaf_nodes.extend(await self._find_leaf_nodes(child_id, nodes, visited))
        
        return leaf_nodes
    
    async def _expand_summary_to_leaves(
        self,
        session: AsyncSession,
        tenant_id: str,
        kb_ids: list[str],
        results: list[dict],
    ) -> list[dict]:
        """
        将摘要节点展开为对应的原始 chunks
        
        当检索结果包含摘要节点（level > 0）时，回溯找到对应的原始 chunks
        
        Args:
            session: 数据库会话
            tenant_id: 租户 ID
            kb_ids: 知识库 ID 列表
            results: 原始检索结果
            
        Returns:
            展开后的检索结果
        """
        from app.models.raptor_node import RaptorNode
        from app.models.chunk import Chunk
        
        # 检查是否有摘要节点需要展开
        summary_results = [r for r in results if r.get("raptor_level", 0) > 0]
        if not summary_results:
            return results
        
        logger.info(
            "[RAPTOR] Step 4: 展开摘要节点 (%d 个摘要节点需要展开)...",
            len(summary_results)
        )
        expand_start = time.time()
        
        # 加载完整的节点树
        nodes = await self._load_raptor_tree(session, tenant_id, kb_ids)
        
        # 收集需要展开的摘要节点 ID
        raptor_node_ids = [r.get("raptor_node_id") for r in summary_results if r.get("raptor_node_id")]
        
        # 查找所有叶子节点
        leaf_node_ids = set()
        summary_to_leaves = {}  # 记录摘要到叶子的映射关系
        
        for raptor_node_id in raptor_node_ids:
            if raptor_node_id:
                leaves = await self._find_leaf_nodes(raptor_node_id, nodes)
                leaf_ids = [leaf["id"] for leaf in leaves]
                summary_to_leaves[raptor_node_id] = leaf_ids
                leaf_node_ids.update(leaf_ids)
        
        if not leaf_node_ids:
            logger.info("[RAPTOR] Step 4 完成: 无叶子节点可展开")
            return results
        
        # 从数据库获取叶子节点的 chunk 信息
        leaf_stmt = (
            select(RaptorNode)
            .where(RaptorNode.id.in_(list(leaf_node_ids)))
        )
        leaf_result = await session.execute(leaf_stmt)
        leaf_nodes_db = {node.id: node for node in leaf_result.scalars().all()}
        
        # 获取对应的原始 Chunk 信息
        chunk_ids = [node.chunk_id for node in leaf_nodes_db.values() if node.chunk_id]
        chunks_map = {}
        if chunk_ids:
            chunk_stmt = select(Chunk).where(Chunk.id.in_(chunk_ids))
            chunk_result = await session.execute(chunk_stmt)
            chunks_map = {chunk.id: chunk for chunk in chunk_result.scalars().all()}
        
        # 构建新的结果列表
        expanded_results = []
        seen_chunk_ids = set()  # 去重
        
        # 先添加非摘要节点（原始 chunks）
        for r in results:
            if r.get("raptor_level", 0) == 0:
                if r.get("chunk_id") not in seen_chunk_ids:
                    expanded_results.append(r)
                    seen_chunk_ids.add(r.get("chunk_id"))
        
        # 展开摘要节点
        for r in summary_results:
            raptor_node_id = r.get("raptor_node_id")
            if not raptor_node_id or raptor_node_id not in summary_to_leaves:
                continue
            
            original_score = r.get("score", 0.5)
            summary_text = r.get("text", "")[:100]  # 摘要预览
            
            for leaf_id in summary_to_leaves[raptor_node_id]:
                leaf_node = leaf_nodes_db.get(leaf_id)
                if not leaf_node or not leaf_node.chunk_id:
                    continue
                
                if leaf_node.chunk_id in seen_chunk_ids:
                    continue
                seen_chunk_ids.add(leaf_node.chunk_id)
                
                chunk = chunks_map.get(leaf_node.chunk_id)
                if not chunk:
                    continue
                
                # 构建展开后的结果
                expanded_result = {
                    "chunk_id": chunk.id,
                    "text": chunk.text,
                    "score": original_score * 0.9,  # 稍微降低分数
                    "metadata": chunk.extra_metadata or {},
                    "knowledge_base_id": str(chunk.knowledge_base_id),
                    "document_id": str(chunk.document_id) if chunk.document_id else None,
                    "source": "raptor",
                    "raptor_mode": self.mode,
                    "raptor_level": 0,
                    "raptor_expanded_from": raptor_node_id,
                    "raptor_summary_preview": summary_text,
                    "raptor_fallback": False,
                }
                expanded_results.append(expanded_result)
        
        expand_time = time.time() - expand_start
        logger.info(
            "[RAPTOR] Step 4 完成: 展开 %d 个摘要 → %d 个原始 chunks (耗时 %.1fms)",
            len(summary_results),
            len(expanded_results) - len([r for r in results if r.get("raptor_level", 0) == 0]),
            expand_time * 1000
        )
        
        return expanded_results
    
    async def _tree_traversal_retrieve(
        self,
        query: str,
        tenant_id: str,
        kb_ids: list[str],
        top_k: int,
        session: AsyncSession,
        **kwargs: Any,
    ) -> list[dict]:
        """
        tree_traversal 模式检索
        
        从最高层摘要开始，逐层向下筛选，最终返回叶子节点。
        
        流程：
        1. 加载 RAPTOR 树结构
        2. 获取最高层节点
        3. 对最高层进行向量检索，选出 top-k
        4. 对选中节点的子节点进行向量检索
        5. 重复直到到达叶子层
        6. 返回最终的叶子节点
        """
        from app.models.raptor_node import RaptorNode
        from app.models.chunk import Chunk
        from app.infra.embeddings import get_embedding
        from app.config import get_settings
        import numpy as np
        
        settings = get_settings()
        
        logger.info("[RAPTOR-Tree] Step 1: 加载 RAPTOR 树结构...")
        tree_start = time.time()
        
        # 加载完整的节点树
        nodes = await self._load_raptor_tree(session, tenant_id, kb_ids)
        if not nodes:
            logger.warning("[RAPTOR-Tree] 无 RAPTOR 节点，回退到 collapsed 模式")
            return await self._fallback_retrieve(
                query=query,
                tenant_id=tenant_id,
                kb_ids=kb_ids,
                top_k=top_k,
                **kwargs,
            )
        
        # 按层级分组节点
        nodes_by_level: dict[int, list[dict]] = {}
        min_level = float('inf')
        max_level = float('-inf')
        for node in nodes.values():
            level = node["level"]
            if level not in nodes_by_level:
                nodes_by_level[level] = []
            nodes_by_level[level].append(node)
            min_level = min(min_level, level)
            max_level = max(max_level, level)
        
        # 处理只有单层节点的情况（RAPTOR 索引未完成构建）
        if min_level == max_level:
            logger.warning(
                "[RAPTOR-Tree] 只有单层节点 (level=%d)，RAPTOR 树未完成构建，使用扁平化检索",
                min_level
            )
            # 回退到 collapsed 模式
            return await self._fallback_retrieve(
                query=query,
                tenant_id=tenant_id,
                kb_ids=kb_ids,
                top_k=top_k,
                **kwargs,
            )
        
        logger.info(
            "[RAPTOR-Tree] Step 1 完成: %d 节点, 层级范围 [%d, %d] (耗时 %.1fms)",
            len(nodes),
            int(min_level),
            int(max_level),
            (time.time() - tree_start) * 1000
        )
        
        # 获取查询向量
        logger.info("[RAPTOR-Tree] Step 2: 查询向量化...")
        embed_start = time.time()
        
        # 使用 embedding_config 或默认配置
        embed_provider = settings.embedding_provider
        embed_model = settings.embedding_model
        if self.embedding_config:
            embed_provider = self.embedding_config.get("provider", embed_provider)
            embed_model = self.embedding_config.get("model", embed_model)
        
        query_embedding = await get_embedding(
            text=query,
            provider=embed_provider,
            model=embed_model,
        )
        query_vec = np.array(query_embedding)
        
        logger.info(
            "[RAPTOR-Tree] Step 2 完成: 向量维度 %d (耗时 %.1fms)",
            len(query_embedding),
            (time.time() - embed_start) * 1000
        )
        
        # 从最高层开始向下遍历
        logger.info("[RAPTOR-Tree] Step 3: 从 Layer %d 开始向下遍历...", max_level)
        traverse_start = time.time()
        
        # 每层选择的节点数（可以配置）
        top_k_per_level = max(top_k * 2, 10)  # 每层多选一些，最后再筛选
        
        # 当前层选中的节点 ID
        current_node_ids: set[str] = set()
        
        # 从最高层开始
        for level in range(max_level, -1, -1):
            level_nodes = nodes_by_level.get(level, [])
            
            if level == max_level:
                # 最高层：直接对所有节点计算相似度
                candidates = level_nodes
            else:
                # 非最高层：只考虑上一层选中节点的子节点
                candidates = []
                for node in level_nodes:
                    # 检查该节点的父节点是否在上一层被选中
                    parent_id = node.get("parent_id")
                    if parent_id and parent_id in current_node_ids:
                        candidates.append(node)
                    elif not parent_id and level == 0:
                        # 叶子节点可能没有 parent_id，检查是否被任何选中节点引用
                        for selected_id in current_node_ids:
                            selected_node = nodes.get(selected_id)
                            if selected_node and node["id"] in selected_node.get("children_ids", []):
                                candidates.append(node)
                                break
            
            if not candidates:
                logger.info("[RAPTOR-Tree] Layer %d: 无候选节点", level)
                continue
            
            # 计算候选节点与查询的相似度
            scored_candidates = []
            for node in candidates:
                # 从向量库获取节点向量（通过 vector_id）
                vector_id = node.get("vector_id")
                if vector_id:
                    # 使用 Qdrant 获取向量
                    try:
                        from app.infra.vector_store import get_qdrant_client
                        qdrant = get_qdrant_client()
                        # 获取向量
                        points = qdrant.retrieve(
                            collection_name="kb_shared",
                            ids=[vector_id],
                            with_vectors=True,
                        )
                        if points and points[0].vector:
                            node_vec = np.array(points[0].vector)
                            # 计算余弦相似度
                            similarity = float(np.dot(query_vec, node_vec) / (
                                np.linalg.norm(query_vec) * np.linalg.norm(node_vec) + 1e-8
                            ))
                            scored_candidates.append((node, similarity))
                    except Exception as e:
                        logger.debug("获取向量失败: %s", e)
                        # 如果获取向量失败，使用文本相似度作为备选
                        scored_candidates.append((node, 0.5))
                else:
                    # 没有 vector_id，使用默认分数
                    scored_candidates.append((node, 0.5))
            
            # 按相似度排序，选择 top-k
            scored_candidates.sort(key=lambda x: x[1], reverse=True)
            selected = scored_candidates[:top_k_per_level]
            
            # 更新当前层选中的节点
            current_node_ids = {node["id"] for node, _ in selected}
            
            logger.info(
                "[RAPTOR-Tree] Layer %d: %d 候选 → %d 选中 (top score: %.3f)",
                level,
                len(candidates),
                len(selected),
                selected[0][1] if selected else 0
            )
        
        traverse_time = time.time() - traverse_start
        logger.info(
            "[RAPTOR-Tree] Step 3 完成: 遍历完成 (耗时 %.1fms)",
            traverse_time * 1000
        )
        
        # 收集最终的叶子节点
        logger.info("[RAPTOR-Tree] Step 4: 构建结果...")
        result_start = time.time()
        
        # 获取叶子节点（level=0）的 chunk 信息
        leaf_nodes = [nodes[nid] for nid in current_node_ids if nodes.get(nid, {}).get("level") == 0]
        
        # 如果没有叶子节点，展开选中的摘要节点
        if not leaf_nodes:
            for nid in current_node_ids:
                node = nodes.get(nid)
                if node and node["level"] > 0:
                    leaves = await self._find_leaf_nodes(nid, nodes)
                    leaf_nodes.extend(leaves)
        
        # 去重
        seen_ids = set()
        unique_leaves = []
        for leaf in leaf_nodes:
            if leaf["id"] not in seen_ids:
                seen_ids.add(leaf["id"])
                unique_leaves.append(leaf)
        
        # 获取对应的 Chunk 信息
        chunk_ids = [leaf.get("chunk_id") for leaf in unique_leaves if leaf.get("chunk_id")]
        chunks_map = {}
        if chunk_ids:
            chunk_stmt = select(Chunk).where(Chunk.id.in_(chunk_ids))
            chunk_result = await session.execute(chunk_stmt)
            chunks_map = {str(chunk.id): chunk for chunk in chunk_result.scalars().all()}
        
        # 构建结果
        results = []
        for i, leaf in enumerate(unique_leaves[:top_k]):
            chunk_id = leaf.get("chunk_id")
            chunk = chunks_map.get(chunk_id) if chunk_id else None
            
            result = {
                "chunk_id": chunk_id,
                "text": chunk.text if chunk else leaf.get("text", ""),
                "score": 1.0 - (i * 0.05),  # 按顺序递减分数
                "metadata": chunk.extra_metadata if chunk else leaf.get("metadata", {}),
                "knowledge_base_id": str(chunk.knowledge_base_id) if chunk else "",
                "document_id": str(chunk.document_id) if chunk and chunk.document_id else None,
                "source": "raptor",
                "raptor_mode": "tree_traversal",
                "raptor_level": 0,
                "raptor_node_id": leaf["id"],
                "raptor_fallback": False,
            }
            results.append(result)
        
        result_time = time.time() - result_start
        logger.info(
            "[RAPTOR-Tree] Step 4 完成: %d 个结果 (耗时 %.1fms)",
            len(results),
            result_time * 1000
        )
        
        return results
