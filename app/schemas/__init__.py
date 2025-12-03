"""
数据模式层 (Schemas)

使用 Pydantic 定义 API 的请求和响应模型：
- 自动数据验证
- 自动生成 OpenAPI 文档
- 类型安全的序列化/反序列化
"""

from app.schemas.config import (
    ChunkerConfig,
    IngestionConfig,
    KBConfig,
    QueryConfig,
    RetrieverConfig,
)
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
from app.schemas.api_key import APIKeyCreate, APIKeyInfo, APIKeySecret, APIKeyUpdate, APIKeyRole
from app.schemas.tenant import (
    TenantCreate,
    TenantCreateResponse,
    TenantDisableRequest,
    TenantListResponse,
    TenantResponse,
    TenantStatus,
    TenantUpdate,
)

__all__ = [
    # Config schemas
    "ChunkerConfig",
    "RetrieverConfig",
    "IngestionConfig",
    "QueryConfig",
    "KBConfig",
    # API Key schemas
    "APIKeyCreate",
    "APIKeyInfo",
    "APIKeySecret",
    "APIKeyUpdate",
    "APIKeyRole",
    # Tenant schemas
    "TenantCreate",
    "TenantCreateResponse",
    "TenantDisableRequest",
    "TenantListResponse",
    "TenantResponse",
    "TenantStatus",
    "TenantUpdate",
    # KB schemas
    "KnowledgeBaseCreate",
    "KnowledgeBaseListResponse",
    "KnowledgeBaseResponse",
    "KnowledgeBaseUpdate",
    # Document schemas
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
    # Query schemas
    "ChunkHit",
    "ModelInfo",
    "RetrieveRequest",
    "RetrieveResponse",
]
