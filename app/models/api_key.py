"""
API 密钥模型 (APIKey)

API Key 用于服务间调用认证，类似 OpenAI 的 API Key 机制。

安全设计：
- API Key 只在创建时显示一次，之后只存储哈希值
- 使用前缀 (prefix) 快速定位，避免全表扫描
- 支持过期时间和手动撤销
- 支持独立的限流配置

API Key 格式示例：
    kb_sk_xxxxxxxxxxxxxxxxxxxx
    ├─────┤└──────────────────┤
    prefix      随机部分

角色权限（在 schemas/api_key.py 中用 Literal 验证）：
- admin: 全部权限 + 管理 API Key
- write: 创建/删除 KB、上传文档、检索
- read: 仅检索和列表
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TIMESTAMP_PK, TimestampMixin


class APIKey(TimestampMixin, Base):
    """
    API 密钥表
    
    存储租户的 API 访问凭证。
    每个租户可以创建多个 API Key，用于不同的应用场景。
    
    认证流程：
    1. 客户端在请求头中携带 API Key
    2. 服务端通过前缀快速查找
    3. 验证哈希值是否匹配
    4. 检查是否过期或被撤销
    """
    __tablename__ = "api_keys"
    
    # 哈希值唯一约束
    __table_args__ = (
        UniqueConstraint("hashed_key", name="uq_api_keys_hashed_key"),
    )

    # 主键
    id: Mapped[TIMESTAMP_PK] = mapped_column(
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
    
    # API Key 名称：用于识别用途，如 "生产环境"、"测试用"
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Key 前缀：如 "kb_sk_abc"，用于快速查找
    # 前缀是明文存储的，哈希值通过前缀定位后再比对
    prefix: Mapped[str] = mapped_column(String(12), index=True)
    
    # Key 哈希值：完整 Key 的 SHA256 哈希，用于验证
    hashed_key: Mapped[str] = mapped_column(String(128), nullable=False)
    
    # 是否已撤销：撤销后立即失效，不可恢复
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # 过期时间：为空表示永不过期
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    
    # 最后使用时间：用于审计和清理长期未使用的 Key
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    
    # 单独的限流配置：覆盖全局限流设置，为空使用默认值
    rate_limit_per_minute: Mapped[int | None] = mapped_column()
    
    # ==================== 新增字段 ====================
    
    # 角色权限：admin/write/read（Pydantic 层验证）
    role: Mapped[str] = mapped_column(String(20), default="write", nullable=False)
    
    # KB 白名单：限制只能访问指定 KB（JSON 数组），空表示不限制
    scope_kb_ids: Mapped[list | None] = mapped_column(JSON)
    
    # 是否为初始管理员 Key：创建租户时自动生成的第一个 Key
    is_initial: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Key 描述/备注
    description: Mapped[str | None] = mapped_column(Text)
