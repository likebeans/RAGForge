"""
管理员 Token 模型 (AdminToken)

存储管理员访问凭证的哈希值，支持多个管理员 Token。

安全设计：
- Token 使用 SHA256 哈希存储
- 支持过期时间
- 支持撤销
- 记录使用情况
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TIMESTAMP_PK, TimestampMixin


class AdminToken(TimestampMixin, Base):
    """
    管理员 Token 表
    
    存储管理员访问凭证，用于访问 /admin/* 接口。
    支持多个 Token，便于不同管理员使用独立凭证。
    """
    __tablename__ = "admin_tokens"

    # 主键
    id: Mapped[TIMESTAMP_PK] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    
    # Token 名称：用于识别用途，如 "主管理员"、"运维团队"
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Token 前缀：如 "admin_xxx"，用于快速查找（明文存储）
    prefix: Mapped[str] = mapped_column(String(12), index=True)
    
    # Token 哈希值：完整 Token 的 SHA256 哈希
    hashed_token: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    
    # 是否已撤销：撤销后立即失效
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    
    # 过期时间：为空表示永不过期
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    
    # 最后使用时间：用于审计
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    
    # Token 描述/备注
    description: Mapped[str | None] = mapped_column(Text)
    
    # 创建者信息（可选）
    created_by: Mapped[str | None] = mapped_column(String(255))
