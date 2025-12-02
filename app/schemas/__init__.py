"""
数据模式层 (Schemas)

使用 Pydantic 定义 API 的请求和响应模型：
- 自动数据验证
- 自动生成 OpenAPI 文档
- 类型安全的序列化/反序列化
"""

from app.schemas.kb import (
    KnowledgeBaseCreate,
    KnowledgeBaseListResponse,
    KnowledgeBaseResponse,
    KnowledgeBaseUpdate,
)
from app.schemas.document import (
    BatchIngestRequest,
    BatchIngestResponse,
    BatchIngestResult,
    ChunkListResponse,
    ChunkResponse,
    DocumentIngestRequest,
    DocumentIngestResponse,
    DocumentListResponse,
    DocumentDetailResponse,
    DocumentResponse,
)
from app.schemas.query import ChunkHit, ModelInfo, RetrieveRequest, RetrieveResponse
from app.schemas.api_key import APIKeyCreate, APIKeyInfo, APIKeySecret, APIKeyUpdate

__all__ = [
    "APIKeyCreate",
    "APIKeyInfo",
    "APIKeySecret",
    "APIKeyUpdate",
    "KnowledgeBaseCreate",
    "KnowledgeBaseListResponse",
    "KnowledgeBaseResponse",
    "KnowledgeBaseUpdate",
    "BatchIngestRequest",
    "BatchIngestResponse",
    "BatchIngestResult",
    "DocumentIngestRequest",
    "DocumentIngestResponse",
    "DocumentListResponse",
    "DocumentDetailResponse",
    "DocumentResponse",
    "ChunkListResponse",
    "ChunkResponse",
    "ChunkHit",
    "RetrieveRequest",
    "RetrieveResponse",
]
