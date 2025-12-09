"""
父子分块切分器

支持两种父块模式：
1. paragraph: 按分隔符和最大长度将文本拆分为段落作为父块
2. full_doc: 整个文档作为父块（超过 10000 字符会截断）

子块用于检索，父块用作上下文。
"""

from __future__ import annotations

from app.pipeline.base import BaseChunkerOperator, ChunkPiece
from app.pipeline.registry import register_operator


# 预定义分隔符映射
SEPARATOR_MAP = {
    "\\n\\n": "\n\n",
    "\\n": "\n",
    "\\t": "\t",
    "。": "。",
    ".": ".",
    "；": "；",
    ";": ";",
}


def _parse_separator(sep: str) -> str:
    """解析分隔符，支持转义序列"""
    return SEPARATOR_MAP.get(sep, sep)


@register_operator("chunker", "parent_child")
class ParentChildChunker(BaseChunkerOperator):
    """
    父子分块切分器
    
    子块用于检索，父块用作上下文。支持两种父块模式：
    - paragraph: 按分隔符分段
    - full_doc: 整个文档作为父块
    """

    name = "parent_child"
    kind = "chunker"
    
    # 全文模式最大字符数（约 10000 tokens）
    MAX_FULL_DOC_CHARS = 40000

    def __init__(
        self,
        # 父块配置
        parent_mode: str = "paragraph",  # paragraph 或 full_doc
        parent_separator: str = "\\n\\n",
        parent_max_chars: int = 1024,
        # 子块配置
        child_separator: str = "\\n",
        child_max_chars: int = 512,
    ):
        """
        Args:
            parent_mode: 父块模式，'paragraph' 按分隔符分段，'full_doc' 整个文档
            parent_separator: 父块分隔符（仅 paragraph 模式）
            parent_max_chars: 父块最大长度（仅 paragraph 模式）
            child_separator: 子块分隔符
            child_max_chars: 子块最大长度
        """
        self.parent_mode = parent_mode
        self.parent_separator = _parse_separator(parent_separator)
        self.parent_max_chars = parent_max_chars
        self.child_separator = _parse_separator(child_separator)
        self.child_max_chars = child_max_chars

    def chunk(self, text: str, metadata: dict | None = None) -> list[ChunkPiece]:
        if not text:
            return []

        base_meta = metadata or {}
        pieces: list[ChunkPiece] = []
        
        # 根据模式生成父块
        if self.parent_mode == "full_doc":
            # 全文模式：整个文档作为一个父块（截断超长文本）
            parent_texts = [text[:self.MAX_FULL_DOC_CHARS]]
        else:
            # 段落模式：按分隔符和最大长度分段
            parent_texts = self._split_to_parents(text)
        
        # 处理每个父块
        for p_idx, parent_text in enumerate(parent_texts):
            parent_id = f"p_{p_idx}"
            
            # 添加父块
            pieces.append(
                ChunkPiece(
                    text=parent_text,
                    metadata={
                        **base_meta,
                        "chunk_id": parent_id,
                        "child": False,
                        "parent_mode": self.parent_mode,
                    }
                )
            )
            
            # 对父块内容生成子块
            children = self._split_to_children(parent_text)
            for c_idx, child_text in enumerate(children):
                pieces.append(
                    ChunkPiece(
                        text=child_text,
                        metadata={
                            **base_meta,
                            "parent_id": parent_id,
                            "child": True,
                            "child_index": c_idx + 1,
                        }
                    )
                )
        
        return pieces

    def _split_to_parents(self, text: str) -> list[str]:
        """按分隔符和最大长度分割为父块"""
        if not self.parent_separator:
            # 无分隔符，按固定长度分割
            return self._split_by_length(text, self.parent_max_chars)
        
        # 先按分隔符分割
        raw_parts = text.split(self.parent_separator)
        parents: list[str] = []
        current = ""
        
        for part in raw_parts:
            part = part.strip()
            if not part:
                continue
            
            # 检查是否需要合并
            if current and len(current) + len(part) + len(self.parent_separator) <= self.parent_max_chars:
                current += self.parent_separator + part
            else:
                if current:
                    parents.append(current)
                # 处理超长段落
                if len(part) > self.parent_max_chars:
                    parents.extend(self._split_by_length(part, self.parent_max_chars))
                    current = ""
                else:
                    current = part
        
        if current:
            parents.append(current)
        
        return parents if parents else [text[:self.parent_max_chars]]

    def _split_to_children(self, text: str) -> list[str]:
        """将文本分割为子块"""
        if not self.child_separator:
            return self._split_by_length(text, self.child_max_chars)
        
        # 先按分隔符分割
        raw_parts = text.split(self.child_separator)
        children: list[str] = []
        current = ""
        
        for part in raw_parts:
            part = part.strip()
            if not part:
                continue
            
            if current and len(current) + len(part) + len(self.child_separator) <= self.child_max_chars:
                current += self.child_separator + part
            else:
                if current:
                    children.append(current)
                if len(part) > self.child_max_chars:
                    children.extend(self._split_by_length(part, self.child_max_chars))
                    current = ""
                else:
                    current = part
        
        if current:
            children.append(current)
        
        return children if children else [text[:self.child_max_chars]]

    def _split_by_length(self, text: str, max_chars: int) -> list[str]:
        """按固定长度分割"""
        return [text[i:i + max_chars] for i in range(0, len(text), max_chars)]
