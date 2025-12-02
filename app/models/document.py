"""
文档模型 (Document)

文档代表用户上传的原始文件（PDF、Word、文本等）。
文档会被切分成多个 Chunk（片段）进行向量化存储。

处理流程：
    用户上传 → 解析文档 → 切分片段 → 向量化 → 存入向量库
                  │
                  └── Document 记录存储在这里
                            │
                            └── Chunk 记录存储在 chunks 表
"""

from uuid import uuid4

from sqlalchemy import ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TIMESTAMP_PK, TimestampMixin


class Document(TimestampMixin, Base):
    """
    文档表
    
    存储原始文档的元信息（不存储文件内容本身）。
    文件内容被切分后存储在 chunks 表中。
    
    字段说明：
    - id: 文档唯一标识
    - knowledge_base_id: 所属知识库
    - title: 文档标题（通常是文件名）
    - source: 来源类型（pdf/docx/url/text 等）
    - extra_metadata: 扩展元数据（作者、页数、标签等）
    - created_by: 上传者 ID
    """
    __tablename__ = "documents"

    # 主键
    id: Mapped[TIMESTAMP_PK] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    
    # 所属租户（冗余存储，便于查询过滤）
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # 所属知识库
    knowledge_base_id: Mapped[str] = mapped_column(
        ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # 文档标题
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # 文档来源类型：pdf / docx / url / text / markdown 等
    source: Mapped[str | None] = mapped_column(String(50))
    
    # 扩展元数据（JSON 格式）
    # 注意：数据库列名仍为 metadata，避免命名冲突使用属性 extra_metadata
    # 可存储的信息示例：
    # {
    #     "author": "张三",
    #     "pages": 10,
    #     "file_size": 102400,
    #     "tags": ["政策", "2024年"],
    #     "department": "销售部"
    # }
    extra_metadata: Mapped[dict | None] = mapped_column("metadata", JSON, default=dict)
    
    # 创建者 ID（关联到用户或 API Key）
    created_by: Mapped[str | None] = mapped_column(String(64))
    
    # ==================== 文档摘要（Document Summary）====================
    # 文档摘要，用于检索时的查询路由和过滤
    summary: Mapped[str | None] = mapped_column(String(2000))
    
    # 摘要状态：pending / generating / completed / failed / skipped
    summary_status: Mapped[str | None] = mapped_column(String(20), default="pending")
