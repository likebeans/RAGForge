"""
Markdown 感知切分器

借鉴 R2R 的 MarkdownHeaderTextSplitter 实现。
按 Markdown 标题层级分块，保留文档结构信息。
"""

import re
from typing import Tuple

from app.pipeline.base import BaseChunkerOperator, ChunkPiece
from app.pipeline.registry import register_operator


@register_operator("chunker", "markdown")
class MarkdownChunker(BaseChunkerOperator):
    """
    Markdown 感知切分器
    
    切分策略：
    1. 按 Markdown 标题（# / ## / ### 等）分割文档
    2. 每个片段包含标题层级信息作为 metadata
    3. 超长片段会使用 RecursiveChunker 进一步分割
    
    适用场景：
    - Markdown 格式文档
    - 技术文档、Wiki、README
    - 需要保留文档结构的场景
    """
    name = "markdown"
    kind = "chunker"
    
    # 默认跟踪的标题层级
    DEFAULT_HEADERS = [
        ("#", "h1"),
        ("##", "h2"),
        ("###", "h3"),
        ("####", "h4"),
    ]

    def __init__(
        self,
        headers_to_split_on: list[Tuple[str, str]] | str | None = None,
        chunk_size: int = 1024,
        chunk_overlap: int = 256,
        strip_headers: bool = False,
    ):
        """
        Args:
            headers_to_split_on: 要分割的标题列表
                - 格式1: [("#", "h1"), ("##", "h2"), ...]
                - 格式2: 逗号分隔的字符串，如 "#,##,###"
            chunk_size: 超长片段的最大字符数
            chunk_overlap: 超长片段分割时的重叠字符数
            strip_headers: 是否从片段内容中移除标题行
        """
        # 解析标题配置
        if headers_to_split_on is None:
            parsed_headers = self.DEFAULT_HEADERS
        elif isinstance(headers_to_split_on, str):
            # 从逗号分隔的字符串解析，如 "#,##,###"
            parsed_headers = []
            for h in headers_to_split_on.split(","):
                h = h.strip()
                if h:
                    # 根据 # 数量自动生成 h1/h2/h3...
                    level = len(h)
                    parsed_headers.append((h, f"h{level}"))
        else:
            parsed_headers = headers_to_split_on
        
        self.headers_to_split_on = sorted(
            parsed_headers,
            key=lambda x: len(x[0]),
            reverse=True,  # 按标题长度降序，优先匹配更长的（### 先于 #）
        )
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.strip_headers = strip_headers

    def chunk(self, text: str, metadata: dict | None = None) -> list[ChunkPiece]:
        if not text:
            return []
        
        base_metadata = metadata or {}
        
        # 按标题分割
        sections = self._split_by_headers(text)
        
        # 处理每个片段
        result: list[ChunkPiece] = []
        for section_text, header_metadata in sections:
            if not section_text.strip():
                continue
            
            # 合并 metadata
            combined_metadata = {**base_metadata, **header_metadata}
            
            # 如果片段过长，进一步分割
            if len(section_text) > self.chunk_size:
                sub_chunks = self._split_long_section(section_text)
                for sub_chunk in sub_chunks:
                    if sub_chunk.strip():
                        result.append(ChunkPiece(text=sub_chunk, metadata=combined_metadata.copy()))
            else:
                result.append(ChunkPiece(text=section_text, metadata=combined_metadata))
        
        return result

    def _split_by_headers(self, text: str) -> list[Tuple[str, dict]]:
        """按标题分割文档，返回 (内容, header_metadata) 列表"""
        lines = text.split("\n")
        sections: list[Tuple[str, dict]] = []
        
        current_content: list[str] = []
        current_headers: dict[str, str] = {}  # 当前标题层级栈
        
        # 标题正则：行首 # 后跟空格或行尾
        header_patterns = {
            prefix: (name, re.compile(rf"^{re.escape(prefix)}(?:\s+(.*))?$"))
            for prefix, name in self.headers_to_split_on
        }
        
        for line in lines:
            stripped = line.strip()
            matched_header = None
            
            # 检查是否是标题行
            for prefix, (name, pattern) in header_patterns.items():
                match = pattern.match(stripped)
                if match:
                    matched_header = (prefix, name, match.group(1) or "")
                    break
            
            if matched_header:
                prefix, name, header_text = matched_header
                
                # 保存当前片段
                if current_content:
                    section_text = "\n".join(current_content)
                    sections.append((section_text, current_headers.copy()))
                    current_content = []
                
                # 更新标题层级栈
                # 遇到同级或更高级别标题时，清除同级及以下的标题
                level = len(prefix)
                keys_to_remove = [
                    k for k in current_headers
                    if k.startswith("h") and int(k[1]) >= level
                ]
                for k in keys_to_remove:
                    del current_headers[k]
                
                current_headers[name] = header_text.strip()
                
                # 如果不移除标题，把标题行加入内容
                if not self.strip_headers:
                    current_content.append(line)
            else:
                current_content.append(line)
        
        # 处理最后一个片段
        if current_content:
            section_text = "\n".join(current_content)
            sections.append((section_text, current_headers.copy()))
        
        return sections

    def _split_long_section(self, text: str) -> list[str]:
        """分割超长片段，使用简单的段落/行/字符分割策略"""
        # 优先按段落分割
        paragraphs = text.split("\n\n")
        
        result: list[str] = []
        current_chunk = ""
        
        for para in paragraphs:
            if len(current_chunk) + len(para) + 2 <= self.chunk_size:
                if current_chunk:
                    current_chunk += "\n\n" + para
                else:
                    current_chunk = para
            else:
                if current_chunk:
                    result.append(current_chunk)
                
                # 处理 overlap
                if result and self.chunk_overlap > 0:
                    overlap_text = result[-1][-self.chunk_overlap:]
                    current_chunk = overlap_text + "\n\n" + para
                    if len(current_chunk) > self.chunk_size:
                        current_chunk = para
                else:
                    current_chunk = para
                
                # 单段落超长时强制分割
                if len(current_chunk) > self.chunk_size:
                    for i in range(0, len(current_chunk), self.chunk_size - self.chunk_overlap):
                        result.append(current_chunk[i:i + self.chunk_size])
                    current_chunk = ""
        
        if current_chunk:
            result.append(current_chunk)
        
        return result
