"""
向量存储工厂

根据配置选择使用 Qdrant 或 PostgreSQL pgvector
"""

import logging
from typing import Literal, Protocol, Any

from app.config import get_settings

logger = logging.getLogger(__name__)

# 向量存储类型
VectorStoreType = Literal["qdrant", "postgresql", "pg"]


class VectorStoreProtocol(Protocol):
    """向量存储协议"""
    
    async def upsert_chunks(
        self,
        *,
        tenant_id: str,
        chunks: list[dict],
        embedding_config: dict | None = None,
        **kwargs,
    ) -> None:
        """批量写入 chunks"""
        ...
    
    async def search(
        self,
        *,
        query: str,
        tenant_id: str,
        kb_ids: list[str],
        top_k: int = 10,
        embedding_config: dict | None = None,
        **kwargs,
    ) -> list[Any]:
        """相似度搜索"""
        ...
    
    async def delete(
        self,
        *,
        tenant_id: str,
        kb_id: str | None = None,
        chunk_ids: list[str] | None = None,
    ) -> int:
        """删除向量"""
        ...


def get_vector_store_type() -> VectorStoreType:
    """获取配置的向量存储类型"""
    settings = get_settings()
    store_type = getattr(settings, "vector_store", "qdrant").lower()
    
    if store_type in ("pg", "postgresql", "pgvector"):
        return "postgresql"
    return "qdrant"


def get_vector_store() -> VectorStoreProtocol:
    """
    根据配置获取向量存储实例
    
    配置项: VECTOR_STORE (环境变量)
    - qdrant: 使用 Qdrant (默认)
    - postgresql/pg/pgvector: 使用 PostgreSQL pgvector
    
    Returns:
        向量存储实例
    """
    store_type = get_vector_store_type()
    
    if store_type == "postgresql":
        from app.infra.vector_store_pg import get_pg_vector_store
        logger.info("使用 PostgreSQL pgvector 向量存储")
        return get_pg_vector_store()
    else:
        from app.infra.vector_store import vector_store
        logger.info("使用 Qdrant 向量存储")
        return vector_store


# 缓存的向量存储实例
_cached_vector_store: VectorStoreProtocol | None = None


def get_cached_vector_store() -> VectorStoreProtocol:
    """获取缓存的向量存储实例（单例）"""
    global _cached_vector_store
    if _cached_vector_store is None:
        _cached_vector_store = get_vector_store()
    return _cached_vector_store


def is_using_pgvector() -> bool:
    """检查是否使用 PostgreSQL pgvector"""
    return get_vector_store_type() == "postgresql"


def is_using_qdrant() -> bool:
    """检查是否使用 Qdrant"""
    return get_vector_store_type() == "qdrant"
