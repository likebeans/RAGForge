"""
Context Window 后处理器

在检索后扩展命中 chunk 的前后 N 个 chunk，保持上下文连贯性。

特性：
- 仅在同一文档内扩展
- 支持 max_tokens 限制
- 命中 chunk 优先保留
- 找不到相邻块时优雅回退
"""

from dataclasses import dataclass
from typing import Any

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Chunk


@dataclass
class ContextWindowConfig:
    """上下文窗口配置"""
    enabled: bool = True
    before: int = 1          # 向前扩展的 chunk 数
    after: int = 1           # 向后扩展的 chunk 数
    max_tokens: int = 2048   # 最大 token 数（粗略按字符估算）


class ContextWindowPostprocessor:
    """
    上下文窗口后处理器
    
    检索后按 document_id + chunk_index 扩展前后 N 个 chunk。
    
    使用示例：
    ```python
    postprocessor = ContextWindowPostprocessor(before=1, after=1)
    expanded_hits = await postprocessor.process(hits, session)
    ```
    """
    
    def __init__(
        self,
        before: int = 1,
        after: int = 1,
        max_tokens: int = 2048,
    ):
        self.before = before
        self.after = after
        self.max_tokens = max_tokens
    
    async def process(
        self,
        hits: list[dict[str, Any]],
        session: AsyncSession,
    ) -> list[dict[str, Any]]:
        """
        处理检索结果，扩展上下文窗口
        
        Args:
            hits: 原始检索结果
            session: 数据库会话
            
        Returns:
            扩展后的检索结果，每个 hit 增加 context_before 和 context_after 字段
        """
        if not hits:
            return hits
        
        # 按 document_id 分组
        doc_hits: dict[str, list[dict]] = {}
        for hit in hits:
            doc_id = hit.get("document_id")
            if doc_id:
                doc_hits.setdefault(doc_id, []).append(hit)
        
        # 批量查询每个文档的相邻 chunks
        expanded_hits = []
        for hit in hits:
            doc_id = hit.get("document_id")
            chunk_index = hit.get("metadata", {}).get("chunk_index")
            
            if doc_id is None or chunk_index is None:
                # 没有足够信息，直接返回原 hit
                expanded_hits.append(hit)
                continue
            
            # 查询前后 chunks
            context_before, context_after = await self._fetch_neighbors(
                session=session,
                document_id=doc_id,
                chunk_index=chunk_index,
                tenant_id=hit.get("metadata", {}).get("tenant_id"),
            )
            
            # 构建扩展后的 hit
            expanded_hit = hit.copy()
            expanded_hit["context_before"] = context_before
            expanded_hit["context_after"] = context_after
            expanded_hit["context_text"] = self._build_context_text(
                context_before, hit["text"], context_after
            )
            expanded_hits.append(expanded_hit)
        
        return expanded_hits
    
    async def _fetch_neighbors(
        self,
        session: AsyncSession,
        document_id: str,
        chunk_index: int,
        tenant_id: str | None = None,
    ) -> tuple[list[dict], list[dict]]:
        """查询前后相邻的 chunks"""
        # 计算需要查询的 index 范围
        before_indices = list(range(max(0, chunk_index - self.before), chunk_index))
        after_indices = list(range(chunk_index + 1, chunk_index + self.after + 1))
        all_indices = before_indices + after_indices
        
        if not all_indices:
            return [], []
        
        # 查询相邻 chunks
        # 使用 JSON 字段查询 chunk_index
        result = await session.execute(
            select(Chunk).where(
                and_(
                    Chunk.document_id == document_id,
                    # PostgreSQL JSON 查询：metadata->>'chunk_index' 转为整数比较
                    Chunk.extra_metadata["chunk_index"].as_integer().in_(all_indices),
                )
            ).order_by(Chunk.extra_metadata["chunk_index"].as_integer())
        )
        chunks = result.scalars().all()
        
        # 按 index 分组
        chunk_map = {
            ch.extra_metadata.get("chunk_index"): {
                "chunk_id": ch.id,
                "text": ch.text,
                "metadata": ch.extra_metadata or {},
            }
            for ch in chunks
        }
        
        context_before = [chunk_map[i] for i in before_indices if i in chunk_map]
        context_after = [chunk_map[i] for i in after_indices if i in chunk_map]
        
        return context_before, context_after
    
    def _build_context_text(
        self,
        before: list[dict],
        hit_text: str,
        after: list[dict],
    ) -> str:
        """
        构建完整的上下文文本
        
        如果超过 max_tokens，先保留命中 chunk，再按距离截断
        """
        # 简单估算：1 token ≈ 2 个字符（中文），1.5 个字符（英文）
        # 这里用字符数粗略估算
        char_limit = self.max_tokens * 2
        
        parts = []
        current_len = len(hit_text)
        
        # 优先添加命中的 chunk
        hit_part = hit_text
        
        # 添加 before（从最近的开始）
        before_texts = []
        for item in reversed(before):
            text = item["text"]
            if current_len + len(text) <= char_limit:
                before_texts.insert(0, text)
                current_len += len(text)
            else:
                break
        
        # 添加 after
        after_texts = []
        for item in after:
            text = item["text"]
            if current_len + len(text) <= char_limit:
                after_texts.append(text)
                current_len += len(text)
            else:
                break
        
        # 组装
        parts = before_texts + [hit_part] + after_texts
        return "\n\n".join(parts)


async def expand_context_window(
    hits: list[dict[str, Any]],
    session: AsyncSession,
    config: ContextWindowConfig | None = None,
) -> list[dict[str, Any]]:
    """
    便捷函数：扩展检索结果的上下文窗口
    
    Args:
        hits: 原始检索结果
        session: 数据库会话
        config: 配置，None 时使用默认配置
        
    Returns:
        扩展后的检索结果
    """
    if config is None:
        config = ContextWindowConfig()
    
    if not config.enabled:
        return hits
    
    postprocessor = ContextWindowPostprocessor(
        before=config.before,
        after=config.after,
        max_tokens=config.max_tokens,
    )
    return await postprocessor.process(hits, session)
