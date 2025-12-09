"""
递归字符切分器

借鉴 R2R 的 RecursiveCharacterTextSplitter 实现。
按优先级尝试不同分隔符进行分块，优先保持语义完整性。

分隔符优先级："\n\n"（段落）→ "\n"（行）→ " "（空格）→ ""（字符）
"""

from app.pipeline.base import BaseChunkerOperator, ChunkPiece
from app.pipeline.registry import register_operator


@register_operator("chunker", "recursive")
class RecursiveChunker(BaseChunkerOperator):
    """
    递归字符切分器
    
    切分策略：
    1. 尝试用高优先级分隔符（如 \\n\\n）分割文本
    2. 如果分割后片段仍然超过 chunk_size，用下一级分隔符继续分割
    3. 相邻片段保持 overlap 重叠
    
    适用场景：
    - 通用文档，需要保持段落/句子完整性
    - 混合格式文本（含换行、段落等结构）
    """
    name = "recursive"
    kind = "chunker"
    
    # 默认分隔符优先级：段落 → 行 → 空格 → 字符
    DEFAULT_SEPARATORS = ["\n\n", "\n", " ", ""]

    # 预定义分隔符映射（支持转义序列）
    SEPARATOR_MAP = {
        "\\n\\n": "\n\n",
        "\\n": "\n",
        "\\t": "\t",
        "。": "。",
        ".": ".",
        " ": " ",
        "": "",
    }

    def __init__(
        self,
        chunk_size: int = 1024,
        chunk_overlap: int = 256,
        separators: list[str] | str | None = None,
        keep_separator: bool = True,
    ):
        """
        Args:
            chunk_size: 每个片段的最大字符数
            chunk_overlap: 相邻片段的重叠字符数
            separators: 分隔符优先级列表，默认为 ["\\n\\n", "\\n", " ", ""]
                        支持逗号分隔的字符串格式，如 "\\n\\n,\\n,。,."
            keep_separator: 是否保留分隔符在片段中
        """
        if chunk_overlap >= chunk_size:
            raise ValueError(f"chunk_overlap ({chunk_overlap}) 必须小于 chunk_size ({chunk_size})")
        
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.keep_separator = keep_separator
        
        # 解析分隔符：支持字符串格式
        if separators is None:
            self.separators = self.DEFAULT_SEPARATORS
        elif isinstance(separators, str):
            # 从逗号分隔的字符串解析
            raw_seps = [s.strip() for s in separators.split(",") if s.strip()]
            self.separators = [self.SEPARATOR_MAP.get(s, s) for s in raw_seps]
        else:
            self.separators = [self.SEPARATOR_MAP.get(s, s) for s in separators]

    def chunk(self, text: str, metadata: dict | None = None) -> list[ChunkPiece]:
        if not text:
            return []
        
        # 递归分割
        chunks = self._split_text(text, self.separators)
        
        # 合并过小的片段，确保不超过 chunk_size
        merged = self._merge_chunks(chunks)
        
        # 构建结果
        return [
            ChunkPiece(text=chunk, metadata=metadata or {})
            for chunk in merged
            if chunk.strip()  # 过滤空片段
        ]

    def _split_text(self, text: str, separators: list[str]) -> list[str]:
        """递归分割文本"""
        if not separators:
            # 没有更多分隔符，按字符分割
            return self._split_by_char(text)
        
        separator = separators[0]
        remaining_separators = separators[1:]
        
        # 用当前分隔符分割
        if separator == "":
            splits = list(text)
        else:
            splits = text.split(separator)
        
        # 处理分割结果
        result: list[str] = []
        for i, split in enumerate(splits):
            # 如果保留分隔符且不是最后一个片段，加回分隔符
            if self.keep_separator and separator and i < len(splits) - 1:
                split = split + separator
            
            if len(split) <= self.chunk_size:
                result.append(split)
            elif remaining_separators:
                # 片段太大，用更细的分隔符继续分割
                result.extend(self._split_text(split, remaining_separators))
            else:
                # 没有更多分隔符，强制按大小分割
                result.extend(self._split_by_char(split))
        
        return result

    def _split_by_char(self, text: str) -> list[str]:
        """按字符强制分割超长文本"""
        result: list[str] = []
        for i in range(0, len(text), self.chunk_size):
            result.append(text[i:i + self.chunk_size])
        return result

    def _merge_chunks(self, chunks: list[str]) -> list[str]:
        """合并片段，确保每个片段接近 chunk_size，并保持 overlap"""
        if not chunks:
            return []
        
        result: list[str] = []
        current_chunk = ""
        
        for chunk in chunks:
            # 如果加上新片段不超限，合并
            if len(current_chunk) + len(chunk) <= self.chunk_size:
                current_chunk += chunk
            else:
                # 保存当前片段
                if current_chunk:
                    result.append(current_chunk)
                
                # 处理 overlap：从上一个片段末尾取 overlap 长度
                if result and self.chunk_overlap > 0:
                    overlap_text = result[-1][-self.chunk_overlap:]
                    current_chunk = overlap_text + chunk
                    
                    # 如果加了 overlap 后超限，只保留新片段
                    if len(current_chunk) > self.chunk_size:
                        current_chunk = chunk
                else:
                    current_chunk = chunk
                
                # 如果单个片段就超限，直接加入结果
                if len(current_chunk) > self.chunk_size:
                    result.append(current_chunk)
                    current_chunk = ""
        
        # 处理最后一个片段
        if current_chunk:
            result.append(current_chunk)
        
        return result
