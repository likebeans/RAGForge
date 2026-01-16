"""
稠密向量检索器

使用向量相似度进行语义检索，支持 Qdrant 和 PostgreSQL pgvector。
适用于语义匹配场景，能够捕获文本的深层语义信息。
"""

from app.infra.vector_store_factory import get_cached_vector_store, is_using_pgvector
from app.pipeline.base import BaseRetrieverOperator
from app.pipeline.registry import register_operator


@register_operator("retriever", "dense")
class DenseRetriever(BaseRetrieverOperator):
    """
    稠密向量检索器
    
    工作流程：
    1. 将查询语句向量化
    2. 在向量库（Qdrant/pgvector）中按余弦相似度搜索
    3. 返回 top_k 个最相似的片段
    """
    name = "dense"
    kind = "retriever"
    
    def __init__(self, embedding_config: dict | None = None):
        """
        Args:
            embedding_config: 可选的 embedding 配置（来自知识库配置）
        """
        self.embedding_config = embedding_config

    async def retrieve(
        self,
        *,
        query: str,
        tenant_id: str,
        kb_ids: list[str],
        top_k: int,
    ):
        # 获取向量存储实例
        vector_store = get_cached_vector_store()
        
        # 调用向量存储进行检索（异步）
        hits = await vector_store.search(
            query=query,
            tenant_id=tenant_id,
            kb_ids=kb_ids,
            top_k=top_k,
            embedding_config=self.embedding_config,
        )
        
        # 转换为统一的返回格式
        # 支持两种格式：
        # - Qdrant: (score, VectorRecord) 元组
        # - pgvector: VectorRecord 对象（score 在对象属性中）
        results = []
        for item in hits:
            if isinstance(item, tuple):
                # Qdrant 格式: (score, rec)
                score, rec = item
                results.append({
                    "chunk_id": rec.chunk_id,
                    "text": rec.text,
                    "score": score,
                    "metadata": rec.metadata,
                    "knowledge_base_id": rec.knowledge_base_id,
                    "document_id": rec.metadata.get("document_id") if rec.metadata else None,
                })
            else:
                # pgvector 格式: VectorRecord
                rec = item
                results.append({
                    "chunk_id": rec.chunk_id,
                    "text": rec.text,
                    "score": rec.score,
                    "metadata": rec.metadata,
                    "knowledge_base_id": rec.metadata.get("kb_id") if rec.metadata else None,
                    "document_id": rec.metadata.get("document_id") if rec.metadata else None,
                })
        
        return results
