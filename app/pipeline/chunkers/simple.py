"""
简单切分器

按段落切分文本，超长段落按固定长度截断。
适用于结构清晰的文档（如 Markdown、文章）。
"""

from app.pipeline.base import BaseChunkerOperator, ChunkPiece
from app.pipeline.registry import register_operator


@register_operator("chunker", "simple")
class SimpleChunker(BaseChunkerOperator):
    """
    简单切分器
    
    切分策略：
    1. 按换行符分割段落
    2. 短段落直接作为一个片段
    3. 长段落按 max_chars 截断
    """
    name = "simple"
    kind = "chunker"

    def __init__(self, max_chars: int = 800):
        """
        Args:
            max_chars: 单个片段的最大字符数
        """
        self.max_chars = max_chars

    def chunk(self, text: str, metadata: dict | None = None) -> list[ChunkPiece]:
        # 按换行符分割段落
        paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
        pieces: list[ChunkPiece] = []
        
        for para in paragraphs:
            if len(para) <= self.max_chars:
                # 短段落直接作为片段
                pieces.append(ChunkPiece(text=para, metadata=metadata or {}))
                continue
            # 长段落按固定长度截断
            for i in range(0, len(para), self.max_chars):
                pieces.append(ChunkPiece(text=para[i : i + self.max_chars], metadata=metadata or {}))
        
        # 空文本保护：至少返回一个片段
        if not pieces:
            pieces.append(ChunkPiece(text=text[: self.max_chars], metadata=metadata or {}))
        return pieces
