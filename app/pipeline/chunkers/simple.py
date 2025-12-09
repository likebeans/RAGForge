"""
简单切分器

按自定义分隔符切分文本，超长段落按固定长度截断。
适用于结构清晰的文档（如 Markdown、文章）。
"""

import re
from app.pipeline.base import BaseChunkerOperator, ChunkPiece
from app.pipeline.registry import register_operator


# 预定义分隔符映射
SEPARATOR_PRESETS = {
    "\\n\\n": "\n\n",       # 双换行（段落）
    "\\n": "\n",            # 单换行
    "\\t": "\t",            # Tab
    "。": "。",              # 中文句号
    ".": ".",               # 英文句号
    "；": "；",              # 中文分号
    ";": ";",               # 英文分号
}


@register_operator("chunker", "simple")
class SimpleChunker(BaseChunkerOperator):
    """
    简单切分器
    
    切分策略：
    1. 按自定义分隔符分割段落
    2. 短段落直接作为一个片段
    3. 长段落按 max_chars 截断
    """
    name = "simple"
    kind = "chunker"

    def __init__(self, max_chars: int = 800, separator: str = "\\n\\n"):
        """
        Args:
            max_chars: 单个片段的最大字符数
            separator: 分隔符，支持预设值（如 \\n\\n, \\n）或自定义字符串
        """
        self.max_chars = max_chars
        # 解析分隔符：支持转义序列或自定义字符
        self.separator = SEPARATOR_PRESETS.get(separator, separator)
        # 存储原始分隔符用于元数据
        self.separator_display = separator

    def chunk(self, text: str, metadata: dict | None = None) -> list[ChunkPiece]:
        base_meta = metadata or {}
        
        # 按分隔符分割
        if self.separator:
            paragraphs = [p.strip() for p in text.split(self.separator) if p.strip()]
        else:
            # 如果分隔符为空，按行分割
            paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
        
        pieces: list[ChunkPiece] = []
        
        for idx, para in enumerate(paragraphs):
            chunk_meta = {
                **base_meta,
                "separator": self.separator_display,
                "paragraph_index": idx,
            }
            
            if len(para) <= self.max_chars:
                # 短段落直接作为片段
                pieces.append(ChunkPiece(text=para, metadata=chunk_meta))
                continue
            # 长段落按固定长度截断
            sub_idx = 0
            for i in range(0, len(para), self.max_chars):
                sub_meta = {**chunk_meta, "sub_index": sub_idx}
                pieces.append(ChunkPiece(text=para[i : i + self.max_chars], metadata=sub_meta))
                sub_idx += 1
        
        # 空文本保护：至少返回一个片段
        if not pieces:
            pieces.append(ChunkPiece(text=text[: self.max_chars], metadata=base_meta))
        return pieces
