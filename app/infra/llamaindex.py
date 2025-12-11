"""
LlamaIndex 集成模块

封装 LlamaIndex 的向量存储和检索功能，支持：
- Qdrant 向量存储
- Milvus 向量存储
- Elasticsearch 向量存储

提供统一的接口用于构建和查询向量索引。
"""

from __future__ import annotations

from typing import Iterable, List, Optional

from llama_index.core import StorageContext, VectorStoreIndex
from llama_index.core.embeddings import BaseEmbedding
from llama_index.core.schema import TextNode
from llama_index.vector_stores.qdrant import QdrantVectorStore
from qdrant_client import QdrantClient

import asyncio

from app.config import get_settings
from app.infra.embeddings import get_embedding, get_embeddings, deterministic_hash_embed

settings = get_settings()


class HashEmbedding(BaseEmbedding):
    """
    哈希 Embedding 适配器（仅用于测试）
    
    使用确定性哈希生成假向量，无语义信息。
    生产环境请使用 RealEmbedding。
    """

    _dim: int = 1024

    def __init__(self, dim: int = 1024):
        super().__init__()
        self._dim = dim

    @property
    def embed_dim(self) -> int:
        return self._dim

    def _get_query_embedding(self, query: str) -> List[float]:
        return deterministic_hash_embed(query, dim=self._dim)

    def _get_text_embedding(self, text: str) -> List[float]:
        return deterministic_hash_embed(text, dim=self._dim)

    async def _aget_query_embedding(self, query: str) -> List[float]:
        return self._get_query_embedding(query)

    def get_query_embedding(self, query: str) -> List[float]:
        return self._get_query_embedding(query)

    def get_text_embedding(self, text: str) -> List[float]:
        return self._get_text_embedding(text)


class RealEmbedding(BaseEmbedding):
    """
    真实 Embedding 适配器
    
    调用项目配置的 Embedding 服务（Ollama/OpenAI 等），
    生成真实的语义向量。
    
    支持动态 embedding 配置，优先使用传入的配置，否则回退到环境变量。
    """

    _dim: int = 1024
    _embedding_config: dict | None = None

    def __init__(self, dim: int | None = None, embedding_config: dict | None = None):
        super().__init__()
        self._dim = dim or settings.embedding_dim
        self._embedding_config = embedding_config

    @property
    def embed_dim(self) -> int:
        return self._dim

    def _run_async(self, coro):
        """安全地在同步上下文中运行异步函数"""
        try:
            loop = asyncio.get_running_loop()
            # 已经在异步上下文中，使用 nest_asyncio 或创建新线程
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, coro)
                return future.result()
        except RuntimeError:
            # 没有运行中的事件循环，直接运行
            return asyncio.run(coro)

    def _get_embedding_async(self, text: str):
        """根据配置获取 embedding"""
        if self._embedding_config:
            from app.infra.embeddings import get_embeddings_with_config
            return get_embeddings_with_config([text], self._embedding_config)
        return get_embedding(text)

    def _get_query_embedding(self, query: str) -> List[float]:
        if self._embedding_config:
            result = self._run_async(self._get_embedding_async(query))
            return result[0] if isinstance(result, list) and len(result) > 0 else result
        return self._run_async(get_embedding(query))

    def _get_text_embedding(self, text: str) -> List[float]:
        if self._embedding_config:
            result = self._run_async(self._get_embedding_async(text))
            return result[0] if isinstance(result, list) and len(result) > 0 else result
        return self._run_async(get_embedding(text))

    async def _aget_query_embedding(self, query: str) -> List[float]:
        if self._embedding_config:
            from app.infra.embeddings import get_embeddings_with_config
            result = await get_embeddings_with_config([query], self._embedding_config)
            return result[0]
        return await get_embedding(query)

    def get_query_embedding(self, query: str) -> List[float]:
        return self._get_query_embedding(query)

    def get_text_embedding(self, text: str) -> List[float]:
        return self._get_text_embedding(text)

    def _get_text_embeddings(self, texts: List[str]) -> List[List[float]]:
        if self._embedding_config:
            from app.infra.embeddings import get_embeddings_with_config
            return self._run_async(get_embeddings_with_config(texts, self._embedding_config))
        return self._run_async(get_embeddings(texts))


def _qdrant_store(collection_name: str) -> QdrantVectorStore:
    client = QdrantClient(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key,
        timeout=5.0,
        prefer_grpc=False,
    )
    return QdrantVectorStore(
        client=client,
        collection_name=collection_name,
    )


def build_qdrant_index(
    collection_name: str, 
    use_real_embedding: bool = True,
    embedding_config: dict | None = None,
) -> VectorStoreIndex:
    """
    构建 Qdrant 向量索引，默认使用真实 Embedding
    
    Args:
        collection_name: Qdrant 集合名称
        use_real_embedding: 是否使用真实 Embedding（否则使用 Hash）
        embedding_config: 可选的 embedding 配置（来自知识库配置）
    """
    store = _qdrant_store(collection_name)
    if use_real_embedding:
        embed_model = RealEmbedding(dim=settings.embedding_dim, embedding_config=embedding_config)
    else:
        embed_model = HashEmbedding(dim=settings.embedding_dim)
    storage_context = StorageContext.from_defaults(vector_store=store)
    return VectorStoreIndex.from_vector_store(
        vector_store=store,
        storage_context=storage_context,
        embed_model=embed_model,
    )


def build_index_by_store(
    store_type: str,
    tenant_id: str,
    kb_id: str,
    params: dict | None = None,
    use_real_embedding: bool = True,
    embedding_config: dict | None = None,
) -> VectorStoreIndex:
    """
    按存储类型构建向量索引
    
    Args:
        store_type: 存储类型 (qdrant/milvus/es)
        tenant_id: 租户 ID
        kb_id: 知识库 ID
        params: 存储参数
        use_real_embedding: 是否使用真实 Embedding（默认 True）
        embedding_config: 可选的 embedding 配置（来自知识库配置）
    """
    store_type = store_type.lower()
    params = params or {}
    if use_real_embedding:
        embed_model = RealEmbedding(dim=settings.embedding_dim, embedding_config=embedding_config)
    else:
        embed_model = HashEmbedding(dim=settings.embedding_dim)

    if store_type == "qdrant":
        collection_name = f"{settings.qdrant_collection_prefix}{tenant_id}"
        store = _qdrant_store(collection_name)
        storage_context = StorageContext.from_defaults(vector_store=store)
        return VectorStoreIndex.from_vector_store(
            vector_store=store,
            storage_context=storage_context,
            embed_model=embed_model,
        )

    if store_type == "milvus":
        try:
            from llama_index.vector_stores.milvus import MilvusVectorStore
        except ImportError as e:
            raise RuntimeError("未安装 llama-index-vector-stores-milvus") from e

        host = params.get("host") or settings.milvus_host
        port = params.get("port") or settings.milvus_port
        user = params.get("user") or settings.milvus_user
        password = params.get("password") or settings.milvus_password
        secure = params.get("secure", settings.milvus_secure)
        if not host or not port:
            raise RuntimeError("Milvus host/port 未配置")
        collection_name = params.get("collection") or f"{settings.qdrant_collection_prefix}{tenant_id}_{kb_id}"
        index_params = params.get("index_params") or {}
        search_params = params.get("search_params") or {}
        # IVF/PQ 配置示例： {"index_type":"IVF_PQ","metric_type":"COSINE","params":{"nlist":128,"m":16}}
        # HNSW 配置示例： {"index_type":"HNSW","metric_type":"COSINE","params":{"M":16,"efConstruction":200}}
        store = MilvusVectorStore(
            uri=f"http{'s' if secure else ''}://{host}:{port}",
            user=user,
            password=password,
            collection_name=collection_name,
            dim=embed_model.embed_dim,
            overwrite=False,
            index_params=index_params or None,
            search_params=search_params or None,
        )
        storage_context = StorageContext.from_defaults(vector_store=store)
        return VectorStoreIndex.from_vector_store(
            vector_store=store,
            storage_context=storage_context,
            embed_model=embed_model,
        )

    if store_type == "es":
        try:
            from llama_index.vector_stores.elasticsearch import ElasticsearchStore
        except ImportError as e:
            raise RuntimeError("未安装 llama-index-vector-stores-elasticsearch") from e

        hosts = params.get("hosts") or settings.es_hosts
        if not hosts:
            raise RuntimeError("Elasticsearch hosts 未配置")
        index_name = params.get("index") or f"{settings.es_index_prefix}{tenant_id}_{kb_id}"
        body = params.get("body")  # 支持自定义索引 mapping/settings（如 dense_vector 配置）
        es_client_params = {
            "basic_auth": (settings.es_username, settings.es_password) if settings.es_username else None
        }
        store = ElasticsearchStore(
            index_name=index_name,
            es_url=hosts,
            es_client_params=es_client_params,
            index_body=body,
        )
        storage_context = StorageContext.from_defaults(vector_store=store)
        return VectorStoreIndex.from_vector_store(
            vector_store=store,
            storage_context=storage_context,
            embed_model=embed_model,
        )

    raise RuntimeError(f"未知向量存储类型: {store_type}")


def nodes_from_chunks(
    *,
    chunks: Iterable[dict],
) -> list[TextNode]:
    """
    将已有 chunk 数据转换为 LlamaIndex TextNode，用于 BM25/Hybrid 等检索。
    每个 chunk dict 需包含 text/metadata/chunk_id。
    """
    nodes: list[TextNode] = []
    for ch in chunks:
        node = TextNode(
            text=ch["text"],
            id_=ch["chunk_id"],
            metadata=ch.get("metadata", {}) or {},
        )
        nodes.append(node)
    return nodes
