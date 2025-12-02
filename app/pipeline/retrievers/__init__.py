"""
检索器模块

提供多种检索策略：
- DenseRetriever         : 稠密向量检索（基于 Qdrant）
- BM25Retriever          : 稀疏检索（基于 BM25 算法）
- HybridRetriever        : 混合检索（Dense + BM25 加权融合）
- FusionRetriever        : 融合检索（RRF/加权 + 可选 Rerank）
- HyDERetriever          : HyDE 检索（假设文档嵌入）
- LlamaDenseRetriever    : 基于 LlamaIndex 的稠密检索
- LlamaBM25Retriever     : 基于 LlamaIndex 的 BM25 检索
- LlamaHybridRetriever   : 基于 LlamaIndex 的混合检索
- MultiQueryRetriever    : 多查询检索（RAG Fusion 多查询扩展）
- SelfQueryRetriever     : 自查询检索（LLM 解析元数据过滤）
- ParentDocumentRetriever: 父文档检索（检索小块返回父块）
- EnsembleRetriever      : 集成检索（任意组合多个检索器）
"""

from app.pipeline.retrievers.bm25 import BM25Retriever  # noqa: F401
from app.pipeline.retrievers.dense import DenseRetriever  # noqa: F401
from app.pipeline.retrievers.hybrid import HybridRetriever  # noqa: F401
from app.pipeline.retrievers.fusion import FusionRetriever  # noqa: F401
from app.pipeline.retrievers.hyde import HyDERetriever  # noqa: F401
from app.pipeline.retrievers.llama_dense import LlamaDenseRetriever  # noqa: F401
from app.pipeline.retrievers.llama_bm25 import LlamaBM25Retriever  # noqa: F401
from app.pipeline.retrievers.llama_hybrid import LlamaHybridRetriever  # noqa: F401
from app.pipeline.retrievers.multi_query import MultiQueryRetriever  # noqa: F401
from app.pipeline.retrievers.self_query import SelfQueryRetriever  # noqa: F401
from app.pipeline.retrievers.parent_document import ParentDocumentRetriever  # noqa: F401
from app.pipeline.retrievers.ensemble import EnsembleRetriever  # noqa: F401

__all__ = [
    "DenseRetriever",
    "BM25Retriever",
    "HybridRetriever",
    "FusionRetriever",
    "HyDERetriever",
    "LlamaDenseRetriever",
    "LlamaBM25Retriever",
    "LlamaHybridRetriever",
    "MultiQueryRetriever",
    "SelfQueryRetriever",
    "ParentDocumentRetriever",
    "EnsembleRetriever",
]
