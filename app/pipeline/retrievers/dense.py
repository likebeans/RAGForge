"""
稠密向量检索器

使用向量相似度进行语义检索，基于 Qdrant 向量数据库。
适用于语义匹配场景，能够捕获文本的深层语义信息。
"""

from app.infra.vector_store import vector_store
from app.pipeline.base import BaseRetrieverOperator
from app.pipeline.registry import register_operator


@register_operator("retriever", "dense")
class DenseRetriever(BaseRetrieverOperator):
    """
    稠密向量检索器
    
    工作流程：
    1. 将查询语句向量化
    2. 在 Qdrant 中按余弦相似度搜索
    3. 返回 top_k 个最相似的片段
    """
    name = "dense"
    kind = "retriever"

    async def retrieve(
        self,
        *,
        query: str,
        tenant_id: str,
        kb_ids: list[str],
        top_k: int,
    ):
        # 调用向量存储进行检索（异步）
        hits = await vector_store.search(
            query=query,
            tenant_id=tenant_id,
            kb_ids=kb_ids,
            top_k=top_k,
        )
        
        # 转换为统一的返回格式
        return [
            {
                "chunk_id": rec.chunk_id,
                "text": rec.text,
                "score": score,
                "metadata": rec.metadata,
                "knowledge_base_id": rec.knowledge_base_id,
                "document_id": rec.metadata.get("document_id") if rec.metadata else None,
            }
            for score, rec in hits
        ]
