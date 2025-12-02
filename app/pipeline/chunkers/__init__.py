"""
文本切分器模块

提供多种文本切分策略：
- SimpleChunker        : 按段落切分，超长段落按固定长度截断
- SlidingWindowChunker : 滑动窗口切分，保持片段间重叠
- ParentChildChunker   : 父子分块，生成大片段和小片段便于多粒度检索
- RecursiveChunker     : 递归字符切分，优先保持语义边界
- MarkdownChunker      : Markdown 感知切分，按标题层级分块
- CodeChunker          : 代码感知切分，按语法结构分块
- LlamaSentenceChunker : 基于 LlamaIndex 的句子级切分
- LlamaTokenChunker    : 基于 LlamaIndex 的 Token 级切分
- MarkdownSectionChunker : 基于 LlamaIndex 的 Markdown 分节切分
"""

from app.pipeline.chunkers.parent_child import ParentChildChunker  # noqa: F401
from app.pipeline.chunkers.simple import SimpleChunker  # noqa: F401
from app.pipeline.chunkers.sliding_window import SlidingWindowChunker  # noqa: F401
from app.pipeline.chunkers.recursive import RecursiveChunker  # noqa: F401
from app.pipeline.chunkers.markdown import MarkdownChunker  # noqa: F401
from app.pipeline.chunkers.code import CodeChunker  # noqa: F401
from app.pipeline.chunkers.llama_sentence import LlamaSentenceChunker, LlamaTokenChunker  # noqa: F401
from app.pipeline.chunkers.markdown_section import MarkdownSectionChunker  # noqa: F401

__all__ = [
    "SimpleChunker",
    "SlidingWindowChunker",
    "ParentChildChunker",
    "RecursiveChunker",
    "MarkdownChunker",
    "CodeChunker",
    "LlamaSentenceChunker",
    "LlamaTokenChunker",
    "MarkdownSectionChunker",
]
