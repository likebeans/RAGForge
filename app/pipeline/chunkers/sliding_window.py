"""
滑动窗口切分器

使用固定大小的窗口滑动切分文本，相邻片段保持一定重叠。
重叠可以保留上下文信息，提升检索效果。
"""

from app.pipeline.base import BaseChunkerOperator, ChunkPiece
from app.pipeline.registry import register_operator


@register_operator("chunker", "sliding_window")
class SlidingWindowChunker(BaseChunkerOperator):
    """
    滑动窗口切分器
    
    切分策略：
    - 窗口大小固定，按步长滑动
    - 步长 = 窗口大小 - 重叠大小
    - 相邻片段共享重叠部分的文本
    
    示例（window=100, overlap=20）：
    片段1: [0, 100)
    片段2: [80, 180)
    片段3: [160, 260)
    """
    name = "sliding_window"
    kind = "chunker"

    def __init__(self, window: int = 800, overlap: int = 200):
        """
        Args:
            window: 窗口大小（字符数）
            overlap: 相邻片段的重叠大小
        """
        self.window = window
        self.overlap = overlap

    def chunk(self, text: str, metadata: dict | None = None) -> list[ChunkPiece]:
        if not text:
            return []
        
        pieces: list[ChunkPiece] = []
        step = max(1, self.window - self.overlap)  # 滑动步长
        
        for start in range(0, len(text), step):
            end = start + self.window
            pieces.append(ChunkPiece(text=text[start:end], metadata=metadata or {}))
            if end >= len(text):
                break
        
        return pieces
