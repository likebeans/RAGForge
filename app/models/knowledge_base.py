"""
知识库模型 (KnowledgeBase)

知识库是文档的逻辑分组，类似于文件夹。
用户可以创建多个知识库来组织不同主题的文档。

应用场景：
- 按部门划分：销售知识库、技术知识库、HR知识库
- 按项目划分：项目A文档、项目B文档
- 按类型划分：产品手册、FAQ、培训资料
"""

from uuid import uuid4

from sqlalchemy import ForeignKey, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TIMESTAMP_PK, TimestampMixin


class KnowledgeBase(TimestampMixin, Base):
    """
    知识库表
    
    存储知识库的基本信息和配置。
    每个知识库对应向量数据库中的一个 Collection。
    
    字段说明：
    - id: 知识库唯一标识
    - name: 知识库名称，租户内唯一
    - description: 描述信息
    - config: 配置信息（JSON），如分块策略、检索参数等
    """
    __tablename__ = "knowledge_bases"
    
    # 租户内名称唯一
    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_kb_tenant_name"),
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
    
    # 知识库名称
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # 描述信息
    description: Mapped[str | None] = mapped_column(String(500))
    
    # 配置信息（JSON 格式）
    # 可存储的配置示例：
    # {
    #     "chunking": {"method": "sliding_window", "size": 512, "overlap": 50},
    #     "retrieval": {"top_k": 10, "rerank": true},
    #     "embedding_model": "text-embedding-3-small"
    # }
    config: Mapped[dict | None] = mapped_column(JSON, default=dict)
