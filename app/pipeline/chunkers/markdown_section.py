"""
Markdown 分节切分器（基于 LlamaIndex）

优先使用 LlamaIndex 的 MarkdownSectionSplitter/MarkdownNodeParser 进行按标题/段落切分，
保留标题路径等元数据；如依赖不可用，回退到简单的按标题分割。
"""

from __future__ import annotations

import re
from typing import Any

from app.pipeline.base import BaseChunkerOperator, ChunkPiece
from app.pipeline.registry import register_operator

MarkdownSplitterType: Any

try:  # LlamaIndex 优先
    from llama_index.core.node_parser import MarkdownSectionSplitter as _MarkdownSplitter  # type: ignore
    MarkdownSplitterType = _MarkdownSplitter
except Exception:  # pragma: no cover - 兼容不同版本
    try:
        from llama_index.core.node_parser import MarkdownNodeParser as _MarkdownSplitter  # type: ignore
        MarkdownSplitterType = _MarkdownSplitter
    except Exception:  # pragma: no cover
        MarkdownSplitterType = None


def _simple_md_sections(text: str) -> list[tuple[str, str]]:
    """
    简易 Markdown 分节：按标题 (#,##,###) 切分。
    Returns: list[(heading, content)]
    """
    sections: list[tuple[str, str]] = []
    pattern = re.compile(r"(^#{1,6} .+$)", re.MULTILINE)
    parts = pattern.split(text)
    current_heading = "ROOT"
    buf: list[str] = []
    for part in parts:
        if pattern.match(part):
            if buf:
                sections.append((current_heading, "\n".join(buf).strip()))
                buf = []
            current_heading = part.strip()
        else:
            buf.append(part)
    if buf:
        sections.append((current_heading, "\n".join(buf).strip()))
    return sections


@register_operator("chunker", "markdown_section")
class MarkdownSectionChunker(BaseChunkerOperator):
    """Markdown 分节切分"""

    name = "markdown_section"
    kind = "chunker"

    def __init__(self, chunk_size: int = 1200, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk(self, text: str, metadata: dict | None = None) -> list[ChunkPiece]:
        if not text:
            return []

        # 优先使用 LlamaIndex 分节
        if MarkdownSplitterType:
            try:
                splitter = MarkdownSplitterType.from_defaults(  # type: ignore[attr-defined]
                    chunk_size=self.chunk_size, chunk_overlap=self.chunk_overlap
                )
                if hasattr(splitter, "get_nodes_from_documents"):
                    nodes = splitter.get_nodes_from_documents(
                        [{"text": text, "metadata": metadata or {}}]
                    )
                else:
                    # MarkdownSectionSplitter API: split_text
                    nodes = splitter.split_text(text)  # type: ignore[attr-defined]
                    # 标准化为带 metadata 的对象
                    nodes = [
                        type("Node", (), {"text": n, "metadata": metadata or {}}) for n in nodes
                    ]

                return [
                    ChunkPiece(
                        text=getattr(node, "text", "") or "",
                        metadata=(node.metadata or {}) | (metadata or {}),
                    )
                    for node in nodes
                ]
            except Exception:  # pragma: no cover - 回退
                pass

        # 回退：按标题分节，再按 chunk_size 切分
        pieces: list[ChunkPiece] = []
        for heading, section in _simple_md_sections(text):
            if not section:
                continue
            for idx in range(0, len(section), max(1, self.chunk_size - self.chunk_overlap)):
                chunk_text = section[idx : idx + self.chunk_size]
                pieces.append(
                    ChunkPiece(
                        text=chunk_text,
                        metadata={"heading": heading} | (metadata or {}),
                    )
                )
                if idx + self.chunk_size >= len(section):
                    break
        return pieces
