"""
文档片段模型 (Chunk) - RAG 检索的基本单位

数据流向: Document → Chunker → Chunks → Embedder → 向量库
"""

from uuid import uuid4

from sqlalchemy import ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TIMESTAMP_PK, TimestampMixin


class Chunk(TimestampMixin, Base):
    """片段表：存储切分后的文本片段，与向量库通过 vector_id 关联"""
    __tablename__ = "chunks"

    # 主键
    id: Mapped[TIMESTAMP_PK] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4()),
    )
    # 所属租户（冗余存储，便于查询过滤）
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True,
    )  # 所属租户
    # 所属知识库（冗余存储，便于查询过滤）
    knowledge_base_id: Mapped[str] = mapped_column(
        ForeignKey("knowledge_bases.id", ondelete="CASCADE"), nullable=False, index=True,
    )  # 所属知识库
    # 所属文档
    document_id: Mapped[str] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True,
    )  # 所属文档
    # 片段文本内容
    # 使用 Text 类型支持长文本（PostgreSQL 中无长度限制）
    text: Mapped[str] = mapped_column(Text, nullable=False)  # 片段文本内容
    # 片段元数据（JSON 格式）
    # 注意：字段名用 extra_metadata 避免与 SQLAlchemy 的 metadata 冲突
    # 可存储的信息示例：
    # {
    #     "chunk_index": 3,          # 在文档中的顺序
    #     "page": 5,                 # 所在页码
    #     "start_char": 1024,        # 起始字符位置
    #     "end_char": 1536,          # 结束字符位置
    #     "parent_chunk_id": "xxx"   # 父级片段 ID（用于父子分块）
    # }
    extra_metadata: Mapped[dict | None] = mapped_column("metadata", JSON, default=dict)
    
    # 向量数据库中的 ID
    # 用于关联向量库中的向量记录，便于删除和更新
    vector_id: Mapped[str | None] = mapped_column(String(128))
    
    # ==================== 向量索引状态 ====================
    # 索引状态：pending / indexing / indexed / failed
    # - pending: 等待索引
    # - indexing: 正在索引中
    # - indexed: 索引完成
    # - failed: 索引失败，需要重试
    indexing_status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    
    # 索引失败原因（可选）
    indexing_error: Mapped[str | None] = mapped_column(Text)
    
    # 索引重试次数
    indexing_retry_count: Mapped[int] = mapped_column(default=0)
    
    # ==================== Chunk Enrichment ====================
    # 增强后的文本（包含上下文描述、实体、摘要等）
    # 用于改善检索效果，保留原始 text 字段不变
    enriched_text: Mapped[str | None] = mapped_column(Text)
    
    # 增强状态：pending / enriching / completed / failed / skipped
    enrichment_status: Mapped[str | None] = mapped_column(String(20), default="pending")
