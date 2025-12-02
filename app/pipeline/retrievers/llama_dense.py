"""
LlamaIndex 稠密检索器

使用 LlamaIndex 封装的 Qdrant 向量检索，与 LlamaIndex 生态无缝集成。
"""

from llama_index.core import VectorStoreIndex
from llama_index.core.retrievers import BaseRetriever as LlamaBaseRetriever

from app.infra.llamaindex import HashEmbedding, build_qdrant_index
from app.pipeline.base import BaseRetrieverOperator
from app.pipeline.registry import register_operator
from app.config import get_settings

settings = get_settings()


def _qdrant_index(tenant_id: str) -> VectorStoreIndex:
    """根据租户 ID 获取对应的 Qdrant 索引"""
    collection_name = f"{settings.qdrant_collection_prefix}{tenant_id}"
    return build_qdrant_index(collection_name)


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

    def __init__(self, top_k: int = 5, store_type: str = "qdrant", store_params: dict | None = None):
        self.default_top_k = top_k
        self.store_type = store_type.lower()
        self.store_params = store_params or {}

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
            index = _qdrant_index(tenant_id)
        else:
            from app.infra.llamaindex import build_index_by_store

            index = build_index_by_store(
                self.store_type, tenant_id=tenant_id, kb_id=kb_ids[0] if kb_ids else "kb", params=self.store_params
            )

        # 不使用 LlamaIndex 的 filters（版本兼容性问题），改为后处理过滤
        retriever: LlamaBaseRetriever = index.as_retriever(
            similarity_top_k=(top_k or self.default_top_k) * 3,  # 多召回以便过滤
        )
        nodes = retriever.retrieve(query)
        
        results = []
        for node in nodes:
            meta = node.metadata or {}
            kb_id = meta.get("kb_id") or meta.get("knowledge_base_id")
            
            # 按知识库 ID 过滤
            if kb_id and kb_id not in kb_ids:
                continue
            
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
            # 达到 top_k 后停止
            if len(results) >= (top_k or self.default_top_k):
                break
        return results
