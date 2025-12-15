"""
LlamaIndex 稠密检索器

使用 LlamaIndex 封装的 Qdrant 向量检索，与 LlamaIndex 生态无缝集成。
支持 Qdrant/Milvus/Elasticsearch 等多种后端。
"""

import logging

from llama_index.core import VectorStoreIndex
from llama_index.core.retrievers import BaseRetriever as LlamaBaseRetriever
from llama_index.core.vector_stores.types import (
    MetadataFilters,
    MetadataFilter,
    FilterOperator,
)
from qdrant_client.http.exceptions import UnexpectedResponse

from app.infra.llamaindex import HashEmbedding, build_qdrant_index
from app.pipeline.base import BaseRetrieverOperator
from app.pipeline.registry import register_operator
from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


def _qdrant_index(tenant_id: str, embedding_config: dict | None = None) -> VectorStoreIndex:
    """根据租户 ID 获取对应的 Qdrant 索引
    
    注意：默认使用 partition 模式的共享 collection (kb_shared)，
    与入库服务保持一致。
    """
    collection_name = settings.qdrant_shared_collection
    return build_qdrant_index(collection_name, embedding_config=embedding_config)


@register_operator("retriever", "llama_dense")
class LlamaDenseRetriever(BaseRetrieverOperator):
    """
    LlamaIndex 稠密检索器
    
    特点：
    - 使用 LlamaIndex 的 VectorStoreIndex
    - 自动处理向量化和检索
    - 支持多种向量存储后端
    """
    name = "llama_dense"
    kind = "retriever"

    def __init__(
        self, 
        top_k: int = 5, 
        store_type: str = "qdrant", 
        store_params: dict | None = None,
        embedding_config: dict | None = None,
    ):
        """
        Args:
            top_k: 默认返回数量
            store_type: 向量存储类型
            store_params: 存储参数
            embedding_config: 可选的 embedding 配置（来自知识库配置）
        """
        self.default_top_k = top_k
        self.store_type = store_type.lower()
        self.store_params = store_params or {}
        self.embedding_config = embedding_config

    async def retrieve(
        self,
        *,
        query: str,
        tenant_id: str,
        kb_ids: list[str],
        top_k: int,
    ):
        # 获取租户对应的索引，使用 metadata filter 过滤 kb_id
        if self.store_type == "qdrant":
            index = _qdrant_index(tenant_id, embedding_config=self.embedding_config)
        else:
            from app.infra.llamaindex import build_index_by_store

            index = build_index_by_store(
                self.store_type, 
                tenant_id=tenant_id, 
                kb_id=kb_ids[0] if kb_ids else "kb", 
                params=self.store_params,
                embedding_config=self.embedding_config,
            )

        # 使用 LlamaIndex 的 MetadataFilters 在查询时过滤 kb_id
        filters = MetadataFilters(
            filters=[
                MetadataFilter(
                    key="kb_id",
                    operator=FilterOperator.IN,
                    value=kb_ids,
                )
            ]
        )
        
        retriever: LlamaBaseRetriever = index.as_retriever(
            similarity_top_k=top_k or self.default_top_k,
            filters=filters,
        )
        
        try:
            nodes = retriever.retrieve(query)
        except UnexpectedResponse as e:
            # Collection 不存在或 Qdrant 返回错误，返回空结果
            if "doesn't exist" in str(e) or e.status_code == 404:
                logger.warning(f"Collection 不存在，返回空结果: tenant_id={tenant_id}")
                return []
            raise
        
        results = []
        for node in nodes:
            meta = node.metadata or {}
            kb_id = meta.get("kb_id") or meta.get("knowledge_base_id")
            
            results.append(
                {
                    "chunk_id": node.node_id,
                    "text": node.text,
                    "score": node.score or 0.0,
                    "metadata": meta,
                    "knowledge_base_id": kb_id,
                    "document_id": meta.get("document_id"),
                    "source": "dense",
                }
            )
        return results
