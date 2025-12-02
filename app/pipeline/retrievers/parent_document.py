"""
父文档检索器（Parent Document Retriever）

检索小块（child chunks），返回对应的父块（parent chunks）。
适用于需要精确定位但又要保留上下文的场景。

工作原理：
1. 使用 parent_child chunker 切分文档，生成父子关系
2. 检索时匹配小块（更精确）
3. 返回结果时替换为对应的父块（更完整的上下文）

特点：
- 精确定位 + 完整上下文
- 需配合 parent_child chunker 使用
- 自动从 chunk metadata 中提取 parent_id
"""

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import SessionLocal
from app.models import Chunk
from app.pipeline.base import BaseRetrieverOperator
from app.pipeline.registry import register_operator, operator_registry

logger = logging.getLogger(__name__)


@register_operator("retriever", "parent_document")
class ParentDocumentRetriever(BaseRetrieverOperator):
    """
    父文档检索器
    
    使用示例：
    ```python
    # 1. 使用 parent_child chunker 切分文档
    # 2. 使用 parent_document retriever 检索
    retriever = operator_registry.get("retriever", "parent_document")(
        base_retriever="dense",
        return_parent=True,  # 返回父块
    )
    results = await retriever.retrieve(query="问题", ...)
    ```
    """
    
    name = "parent_document"
    kind = "retriever"
    
    def __init__(
        self,
        base_retriever: str = "dense",
        base_retriever_params: dict | None = None,
        return_parent: bool = True,
        include_child: bool = False,
    ):
        """
        Args:
            base_retriever: 底层检索器名称
            base_retriever_params: 底层检索器参数
            return_parent: 是否返回父块（True）还是子块（False）
            include_child: 返回父块时是否同时包含匹配的子块信息
        """
        self.base_retriever_name = base_retriever
        self.base_retriever_params = base_retriever_params or {}
        self.return_parent = return_parent
        self.include_child = include_child
    
    def _get_base_retriever(self) -> BaseRetrieverOperator:
        """获取底层检索器"""
        factory = operator_registry.get("retriever", self.base_retriever_name)
        if not factory:
            raise ValueError(f"未找到检索器: {self.base_retriever_name}")
        return factory(**self.base_retriever_params)
    
    async def _get_parent_chunks(
        self,
        session: AsyncSession,
        parent_ids: set[str],
        tenant_id: str,
        kb_ids: list[str],
    ) -> dict[str, dict]:
        """从数据库获取父块"""
        if not parent_ids:
            return {}
        
        # 查询父块（通过 chunk_id 或 metadata 中的标识）
        # 父块的 chunk_id 通常包含 parent_id 信息
        stmt = select(Chunk).where(
            Chunk.tenant_id == tenant_id,
            Chunk.knowledge_base_id.in_(kb_ids),
        )
        
        result = await session.execute(stmt)
        chunks = result.scalars().all()
        
        parent_map: dict[str, dict] = {}
        for chunk in chunks:
            meta = chunk.extra_metadata or {}
            chunk_parent_id = meta.get("parent_id")
            # 如果是父块本身（没有 child 标记或 parent_id 等于自己的标识）
            is_parent = not meta.get("child", False)
            
            if is_parent and chunk_parent_id in parent_ids:
                parent_map[chunk_parent_id] = {
                    "chunk_id": str(chunk.id),
                    "text": chunk.text,
                    "metadata": meta,
                    "knowledge_base_id": str(chunk.knowledge_base_id),
                    "document_id": str(chunk.document_id) if chunk.document_id else None,
                }
        
        return parent_map
    
    async def retrieve(
        self,
        *,
        query: str,
        tenant_id: str,
        kb_ids: list[str],
        top_k: int,
    ) -> list[dict[str, Any]]:
        """
        执行父文档检索
        
        1. 使用底层检索器检索（匹配子块）
        2. 提取 parent_id
        3. 返回父块或子块
        """
        base_retriever = self._get_base_retriever()
        
        # 检索（多召回一些因为要去重父块）
        recall_k = top_k * 3 if self.return_parent else top_k
        
        results = await base_retriever.retrieve(
            query=query,
            tenant_id=tenant_id,
            kb_ids=kb_ids,
            top_k=recall_k,
        )
        
        if not self.return_parent:
            # 直接返回子块
            for hit in results[:top_k]:
                hit["source"] = "parent_document"
            return results[:top_k]
        
        # 提取 parent_id 并去重
        parent_ids: set[str] = set()
        child_by_parent: dict[str, list[dict]] = {}
        
        for hit in results:
            metadata = hit.get("metadata", {})
            parent_id = metadata.get("parent_id")
            
            if parent_id:
                parent_ids.add(parent_id)
                if parent_id not in child_by_parent:
                    child_by_parent[parent_id] = []
                child_by_parent[parent_id].append(hit)
        
        # 获取父块
        async with SessionLocal() as session:
            parent_chunks = await self._get_parent_chunks(
                session, parent_ids, tenant_id, kb_ids
            )
        
        # 构建结果
        final_results: list[dict] = []
        seen_parents: set[str] = set()
        
        for hit in results:
            metadata = hit.get("metadata", {})
            parent_id = metadata.get("parent_id")
            
            if parent_id and parent_id not in seen_parents:
                seen_parents.add(parent_id)
                
                if parent_id in parent_chunks:
                    # 使用父块
                    parent_hit = parent_chunks[parent_id].copy()
                    parent_hit["score"] = hit.get("score", 0)
                    parent_hit["source"] = "parent_document"
                    parent_hit["parent_id"] = parent_id
                    
                    if self.include_child:
                        # 包含匹配的子块信息
                        parent_hit["matched_children"] = [
                            {"chunk_id": c["chunk_id"], "text": c["text"][:100]}
                            for c in child_by_parent.get(parent_id, [])[:3]
                        ]
                    
                    final_results.append(parent_hit)
                else:
                    # 找不到父块，使用原始结果
                    hit["source"] = "parent_document"
                    hit["parent_not_found"] = True
                    final_results.append(hit)
            
            elif not parent_id:
                # 没有 parent_id 的块直接返回
                hit["source"] = "parent_document"
                final_results.append(hit)
            
            if len(final_results) >= top_k:
                break
        
        return final_results[:top_k]
