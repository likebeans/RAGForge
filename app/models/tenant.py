"""
租户模型 (Tenant)

租户是多租户系统的顶层实体，代表一个企业或组织。
所有数据都通过 tenant_id 进行隔离，确保不同租户的数据互不可见。

多租户架构设计：
- 每个租户有独立的数据空间
- API Key 绑定到租户
- 知识库、文档、用户都属于某个租户

租户状态（在 schemas/tenant.py 中用 Literal 验证）：
- active: 正常运行
- disabled: 已禁用（API 请求被拒绝）
- pending: 待审核（用于自助注册流程）
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TIMESTAMP_PK, TimestampMixin


class Tenant(TimestampMixin, Base):
    """
    租户表
    
    存储企业/组织的基本信息。
    作为数据隔离的根节点，其他所有业务数据都关联到租户。
    
    字段说明：
    - id: 租户唯一标识（UUID 格式）
    - name: 租户名称，全局唯一
    - plan: 订阅计划，影响功能权限和资源配额
    - status: 租户状态（active/disabled/pending）
    - quota_*: 资源配额限制
    """
    __tablename__ = "tenants"

    # 主键：使用 UUID 作为 ID，避免自增 ID 的安全风险和分布式问题
    id: Mapped[TIMESTAMP_PK] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),  # 自动生成 UUID
    )
    
    # 租户名称：用于展示和识别，必须全局唯一
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    
    # 订阅计划：决定租户的功能权限和资源限制
    # 可选值：free（免费）、standard（标准）、enterprise（企业）
    plan: Mapped[str] = mapped_column(String(50), default="standard", nullable=False)
    
    # ==================== 新增字段 ====================
    
    # 租户状态：active/disabled/pending（Pydantic 层验证）
    status: Mapped[str] = mapped_column(
        String(20), 
        default="active", 
        nullable=False,
        index=True,
    )
    
    # 资源配额：知识库数量限制（-1 表示无限制）
    quota_kb_count: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    
    # 资源配额：文档数量限制（-1 表示无限制）
    quota_doc_count: Mapped[int] = mapped_column(Integer, default=1000, nullable=False)
    
    # 资源配额：存储空间限制（MB，-1 表示无限制）
    quota_storage_mb: Mapped[int] = mapped_column(Integer, default=1024, nullable=False)
    
    # 禁用时间：记录租户被禁用的时间
    disabled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    
    # 禁用原因：记录禁用原因，便于审计
    disabled_reason: Mapped[str | None] = mapped_column(Text)
    
    # ==================== 存储隔离配置 ====================
    
    # 向量库隔离策略：
    # - partition: 共享 Collection，按 tenant_id 过滤（适合小客户，节省资源）
    # - collection: 独立 Collection（适合中大客户，性能更好）
    # - auto: 根据数据量自动选择（默认，<10K vectors 用 partition）
    isolation_strategy: Mapped[str] = mapped_column(
        String(20),
        default="auto",
        nullable=False,
    )
