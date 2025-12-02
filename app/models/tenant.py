"""
租户模型 (Tenant)

租户是多租户系统的顶层实体，代表一个企业或组织。
所有数据都通过 tenant_id 进行隔离，确保不同租户的数据互不可见。

多租户架构设计：
- 每个租户有独立的数据空间
- API Key 绑定到租户
- 知识库、文档、用户都属于某个租户
"""

from uuid import uuid4

from sqlalchemy import String
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
