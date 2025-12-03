"""
用量日志模型 (UsageLog)

记录租户的 API 操作日志，用于：
- 用量统计和计费
- 审计追踪
- 配额检查

操作类型 action：
- create_kb: 创建知识库
- delete_kb: 删除知识库
- upload_doc: 上传文档
- delete_doc: 删除文档
- retrieve: 检索
- create_api_key: 创建 API Key
- revoke_api_key: 撤销 API Key
"""

from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class UsageLog(Base):
    """
    用量日志表
    
    记录每次 API 操作，用于统计和审计。
    不使用 TimestampMixin，只需要 created_at。
    """
    __tablename__ = "usage_logs"

    # 主键
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    
    # 所属租户
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # 操作的 API Key（管理员操作可能为空）
    api_key_id: Mapped[str | None] = mapped_column(
        ForeignKey("api_keys.id", ondelete="SET NULL"),
        index=True,
    )
    
    # 操作类型：create_kb/delete_kb/upload_doc/retrieve/...
    action: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    
    # 资源类型：kb/document/chunk/api_key
    resource_type: Mapped[str | None] = mapped_column(String(50))
    
    # 资源 ID
    resource_id: Mapped[str | None] = mapped_column(String(36))
    
    # 额外详情（JSON）：如请求参数、结果数量等
    details: Mapped[dict | None] = mapped_column(JSON)
    
    # 创建时间（自动设置为当前时间）
    created_at: Mapped[str] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
