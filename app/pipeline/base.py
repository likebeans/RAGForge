"""
Pipeline 基础类型定义

定义算法组件的抽象接口，所有切分器和检索器都需实现对应的 Protocol。

设计理念：
- 使用 Protocol 而非抽象基类，提供结构化类型检查
- 统一的 name/kind 属性，便于注册和发现
- 支持同步（Chunker）和异步（Retriever）操作
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class ChunkPiece:
    """
    文本片段数据结构
    
    切分器的输出单元，包含文本内容和元数据。
    """
    text: str       # 片段文本
    metadata: dict  # 元数据（如位置、父级ID等）


class BaseOperator(Protocol):
    """算法组件基础协议"""
    name: str  # 算法名称，如 "simple", "sliding_window"
    kind: str  # 算法类型，如 "chunker", "retriever"


class BaseChunkerOperator(BaseOperator, Protocol):
    """
    切分器协议
    
    所有文本切分算法需实现此接口。
    """
    kind: str = "chunker"

    def chunk(self, text: str, metadata: dict | None = None) -> list[ChunkPiece]:
        """
        将文本切分为多个片段
        
        Args:
            text: 原始文本
            metadata: 附加元数据（会传递到每个片段）
        
        Returns:
            list[ChunkPiece]: 切分后的片段列表
        """
        ...


class BaseRetrieverOperator(BaseOperator, Protocol):
    """
    检索器协议
    
    所有检索算法需实现此接口。
    """
    kind: str = "retriever"

    async def retrieve(
        self,
        *,
        query: str,
        tenant_id: str,
        kb_ids: list[str],
        top_k: int,
    ):
        """
        执行检索
        
        Args:
            query: 查询语句
            tenant_id: 租户 ID
            kb_ids: 知识库 ID 列表
            top_k: 返回结果数量
        
        Returns:
            list[dict]: 检索结果列表
        """
        ...


class BasePipeline:
    """Pipeline 基类，用于未来的算法组合编排"""
    name: str = "base"
