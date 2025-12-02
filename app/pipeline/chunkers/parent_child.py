"""
父子分块切分器（基于 LlamaIndex 的 Parent/Child 解析）

使用 LlamaIndex 的分层切分器生成父子节点，保留 parent-child 关系到 metadata。
在不支持 LlamaIndex 的环境下，回退到简单的字符切分实现。
"""

from __future__ import annotations

from app.pipeline.base import BaseChunkerOperator, ChunkPiece
from app.pipeline.registry import register_operator

try:  # 优先使用 LlamaIndex 的分层切分器
    from llama_index.core.node_parser import ParentChildNodeParser as _ParentChildParser  # type: ignore
except Exception:  # pragma: no cover - 兼容不同版本
    try:
        from llama_index.core.node_parser import HierarchicalNodeParser as _ParentChildParser  # type: ignore
    except Exception:  # pragma: no cover
        _ParentChildParser = None


def _safe_parent_id(node) -> str | None:
    try:
        rel = node.relationships.get("PARENT") if hasattr(node, "relationships") else None
        return getattr(rel, "node_id", None) or getattr(rel, "id", None)
    except Exception:  # pragma: no cover - 兼容性兜底
        return None


@register_operator("chunker", "parent_child")
class ParentChildChunker(BaseChunkerOperator):
    """
    父子分块切分器
    
    优先使用 LlamaIndex 的 ParentChild/Hieararchical 解析，保留父子关系。
    """

    name = "parent_child"
    kind = "chunker"

    def __init__(
        self,
        parent_chars: int = 1600,
        child_chars: int = 400,
        overlap: int = 100,
    ):
        self.parent_chars = parent_chars
        self.child_chars = child_chars
        self.overlap = overlap

    def chunk(self, text: str, metadata: dict | None = None) -> list[ChunkPiece]:
        if not text:
            return []

        # 优先使用 LlamaIndex 的分层切分器
        if _ParentChildParser:
            try:
                parser = _ParentChildParser.from_defaults(
                    chunk_sizes=[self.parent_chars, self.child_chars],
                    chunk_overlap=self.overlap,
                )
                nodes = parser.get_nodes_from_documents(
                    [{"text": text, "metadata": metadata or {}}]
                )
                pieces: list[ChunkPiece] = []
                for node in nodes:
                    parent_id = _safe_parent_id(node)
                    node_meta = (node.metadata or {}).copy()
                    if parent_id:
                        node_meta["parent_id"] = parent_id
                    pieces.append(
                        ChunkPiece(
                            text=getattr(node, "text", "") or "",
                            metadata=node_meta,
                        )
                    )
                if pieces:
                    return pieces
            except Exception:  # pragma: no cover - 回退到简单实现
                pass

        # 回退：简单父子字符切分
        pieces: list[ChunkPiece] = []
        for idx in range(0, len(text), self.parent_chars):
            parent_text = text[idx : idx + self.parent_chars]
            parent_id = f"parent_{idx//self.parent_chars}"
            pieces.append(
                ChunkPiece(text=parent_text, metadata={"parent_id": parent_id} | (metadata or {}))
            )
            step = max(1, self.child_chars - self.overlap)
            for cstart in range(0, len(parent_text), step):
                child_text = parent_text[cstart : cstart + self.child_chars]
                pieces.append(
                    ChunkPiece(
                        text=child_text,
                        metadata={"parent_id": parent_id, "child": True} | (metadata or {}),
                    )
                )
                if cstart + self.child_chars >= len(parent_text):
                    break
        return pieces
