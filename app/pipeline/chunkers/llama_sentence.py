"""
LlamaIndex 切分器

基于 LlamaIndex 提供的切分工具，支持：
- 句子级切分：保持句子完整性，避免截断
- Token 级切分：按 Token 数量切分，适配 LLM 上下文限制
"""

from llama_index.core.node_parser import SentenceSplitter, TokenTextSplitter
from llama_index.core.schema import Document

from app.pipeline.base import BaseChunkerOperator, ChunkPiece
from app.pipeline.registry import register_operator


@register_operator("chunker", "llama_sentence")
class LlamaSentenceChunker(BaseChunkerOperator):
    """
    句子级切分器
    
    使用 LlamaIndex 的 SentenceSplitter，特点：
    - 尊重句子边界，不会截断句子
    - 按 Token 数量控制片段大小
    - 支持多种分词器（tiktoken、huggingface 等）
    """
    name = "llama_sentence"
    kind = "chunker"

    def __init__(self, max_tokens: int = 512, chunk_overlap: int = 50):
        """
        Args:
            max_tokens: 每个片段的最大 Token 数
            chunk_overlap: 相邻片段的重叠 Token 数
        """
        self.splitter = SentenceSplitter(
            chunk_size=max_tokens,
            chunk_overlap=chunk_overlap,
        )

    def chunk(self, text: str, metadata: dict | None = None) -> list[ChunkPiece]:
        doc = Document(text=text, metadata=metadata or {})
        nodes = self.splitter.get_nodes_from_documents([doc])
        return [ChunkPiece(text=node.text, metadata=node.metadata or {}) for node in nodes]


@register_operator("chunker", "llama_token")
class LlamaTokenChunker(BaseChunkerOperator):
    """
    Token 级切分器
    
    严格按 Token 数量切分，适用于需要精确控制上下文长度的场景。
    """
    name = "llama_token"
    kind = "chunker"

    def __init__(self, max_tokens: int = 512, chunk_overlap: int = 50):
        """
        Args:
            max_tokens: 每个片段的最大 Token 数
            chunk_overlap: 相邻片段的重叠 Token 数
        """
        self.splitter = TokenTextSplitter(
            chunk_size=max_tokens,
            chunk_overlap=chunk_overlap,
        )

    def chunk(self, text: str, metadata: dict | None = None) -> list[ChunkPiece]:
        chunks = self.splitter.split_text(text)
        return [ChunkPiece(text=ch, metadata=metadata or {}) for ch in chunks]
