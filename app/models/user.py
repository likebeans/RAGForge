"""
用户模型 (User)

用户是系统的操作者，属于某个租户。
支持基于角色的访问控制（RBAC），通过 roles 字段分配权限。

安全设计：
- 密码使用哈希存储，永不明文保存
- 邮箱在租户内唯一（不同租户可以有相同邮箱）
- 支持禁用用户（is_active = False）
"""

from uuid import uuid4

from sqlalchemy import ForeignKey, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TIMESTAMP_PK, TimestampMixin


class User(TimestampMixin, Base):
    """
    用户表
    
    存储用户账号信息和权限角色。
    
    字段说明：
    - id: 用户唯一标识
    - tenant_id: 所属租户（外键）
    - email: 登录邮箱，租户内唯一
    - hashed_password: 密码哈希值
    - roles: 用户角色列表（JSON 数组）
    - is_active: 账号是否启用
    """
    __tablename__ = "users"
    
    # 表级约束：同一租户内邮箱唯一
    __table_args__ = (
        UniqueConstraint("tenant_id", "email", name="uq_user_tenant_email"),
    )

    # 主键
    id: Mapped[TIMESTAMP_PK] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    
    # 外键：关联到租户表
    # ondelete="CASCADE" 表示删除租户时自动删除其所有用户
    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,  # 建索引加速按租户查询
    )
    
    # 用户邮箱：用于登录和通知
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # 密码哈希：使用 bcrypt 或类似算法加密存储
    # 可为空是为了支持第三方 OAuth 登录（如企业 SSO）
    hashed_password: Mapped[str | None] = mapped_column(String(255))
    
    # 角色列表：存储为 JSON 数组，如 ["admin", "editor"]
    # 用于 RBAC 权限控制
    roles: Mapped[list[str]] = mapped_column(JSON, default=list)
    
    # 账号状态：False 表示禁用，禁止登录
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
