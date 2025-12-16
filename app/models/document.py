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

from sqlalchemy import ForeignKey, JSON, String, Text
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
    
    # ==================== ACL 权限控制 ====================
    # 敏感度级别（简化为两级）：
    # - public: 公开，租户内所有 API Key 可访问
    # - restricted: 受限，需要 ACL 白名单匹配才能访问
    #
    # 注意：数据库中可能存在旧值 internal/confidential/secret，
    # 在 ACL 检查时会被视为 restricted 处理
    sensitivity_level: Mapped[str] = mapped_column(
        String(20),
        default="public",
        nullable=False,
        index=True,
    )
    
    # ACL 白名单：允许访问的用户 ID 列表
    # 为 null 时，根据 sensitivity_level 决定访问权限
    # 格式：["user_id_1", "user_id_2", ...]
    acl_allow_users: Mapped[list | None] = mapped_column("acl_users", JSON)
    
    # ACL 白名单：允许访问的角色列表
    # 格式：["admin", "editor", "viewer", ...]
    acl_allow_roles: Mapped[list | None] = mapped_column("acl_roles", JSON)
    
    # ACL 白名单：允许访问的组/部门列表
    # 格式：["sales", "engineering", "hr", ...]
    acl_allow_groups: Mapped[list | None] = mapped_column("acl_groups", JSON)
    
    # ==================== 原始内容（用于 Ground/Playground 预览）====================
    # 存储原始文件内容，供分块预览等功能使用
    # 只有 Ground 上传的文档会保存此字段，正常知识库文档此字段为空
    raw_content: Mapped[str | None] = mapped_column(Text)
    
    # ==================== 处理状态 ====================
    # 文档入库处理状态：
    # - pending: 等待处理（刚创建，还未开始入库）
    # - processing: 正在处理中
    # - completed: 处理完成
    # - failed: 处理失败
    # - interrupted: 处理中断（服务重启导致）
    processing_status: Mapped[str] = mapped_column(
        String(20), 
        default="pending",
        nullable=False,
        index=True
    )
    
    # ==================== 处理日志 ====================
    # 记录文档入库过程的详细日志，用于前端展示处理进度和排查问题
    # 格式：每行一条日志，包含时间戳和日志内容
    processing_log: Mapped[str | None] = mapped_column(Text)
