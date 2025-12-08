"""
对话模型 (Conversation & Message)

用于持久化前端聊天历史，支持多轮对话和引用来源存储。

数据关系：
    Tenant
       └── Conversation (对话)
              └── Message (消息)
"""

from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TIMESTAMP_PK, TimestampMixin

if TYPE_CHECKING:
    from app.models.tenant import Tenant


class Conversation(TimestampMixin, Base):
    """
    对话表
    
    存储用户的对话会话，每个对话可以关联多个知识库。
    
    字段说明：
    - id: 对话唯一标识
    - tenant_id: 所属租户
    - title: 对话标题（通常从首条消息自动生成）
    - knowledge_base_ids: 关联的知识库 ID 列表
    """
    __tablename__ = "conversations"

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
    
    # 对话标题
    title: Mapped[str | None] = mapped_column(String(255))
    
    # 关联的知识库 ID 列表
    knowledge_base_ids: Mapped[list | None] = mapped_column(JSON, default=list)
    
    # 关系
    messages: Mapped[list["Message"]] = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )
    
    tenant: Mapped["Tenant"] = relationship("Tenant", lazy="selectin")


class Message(TimestampMixin, Base):
    """
    消息表
    
    存储对话中的每条消息，包括用户消息和 AI 回复。
    
    字段说明：
    - id: 消息唯一标识
    - conversation_id: 所属对话
    - role: 消息角色（user/assistant）
    - content: 消息内容
    - retriever: 使用的检索器名称
    - sources: 引用来源（JSON 格式）
    - extra_metadata: 额外元数据（模型信息、耗时等）
    """
    __tablename__ = "messages"

    # 主键
    id: Mapped[TIMESTAMP_PK] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    
    # 所属对话
    conversation_id: Mapped[str] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # 消息角色：user / assistant
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    
    # 消息内容
    content: Mapped[str] = mapped_column(Text, nullable=False)
    
    # 使用的检索器（仅 assistant 消息）
    retriever: Mapped[str | None] = mapped_column(String(50))
    
    # 引用来源（JSON 格式）
    # 结构示例：
    # [
    #   {"text": "...", "score": 0.89, "document_title": "...", "chunk_id": "..."},
    #   ...
    # ]
    sources: Mapped[list | None] = mapped_column(JSON)
    
    # 额外元数据（避免使用 metadata 保留字）
    # 可存储：模型信息、响应耗时、token 使用量等
    extra_metadata: Mapped[dict | None] = mapped_column(
        "metadata",  # 显式指定列名
        JSON,
        default=dict,
    )
    
    # 关系
    conversation: Mapped["Conversation"] = relationship(
        "Conversation",
        back_populates="messages",
    )
