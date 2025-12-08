"""
添加对话和消息表

用于前端聊天历史持久化功能。

- conversations: 对话表，存储对话元信息
- messages: 消息表，存储对话中的消息

Revision ID: f8c3e2b1a5d4
Revises: ea763878e44f
Create Date: 2025-01-15 00:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# 迁移版本标识
revision: str = "f8c3e2b1a5d4"
down_revision: Union[str, None] = "ea763878e44f"  # 上一个迁移
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """升级：创建 conversations 和 messages 表"""
    
    # 创建 conversations 表
    op.create_table(
        "conversations",
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("knowledge_base_ids", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_conversations_tenant_id", "conversations", ["tenant_id"])
    op.create_index("ix_conversations_updated_at", "conversations", ["updated_at"])
    
    # 创建 messages 表
    op.create_table(
        "messages",
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("conversation_id", sa.String(length=36), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("retriever", sa.String(length=50), nullable=True),
        sa.Column("sources", sa.JSON(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),  # 实际列名为 metadata
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_messages_conversation_id", "messages", ["conversation_id"])
    op.create_index("ix_messages_created_at", "messages", ["created_at"])


def downgrade() -> None:
    """降级：删除 messages 和 conversations 表"""
    
    # 删除索引和表
    op.drop_index("ix_messages_created_at", "messages")
    op.drop_index("ix_messages_conversation_id", "messages")
    op.drop_table("messages")
    
    op.drop_index("ix_conversations_updated_at", "conversations")
    op.drop_index("ix_conversations_tenant_id", "conversations")
    op.drop_table("conversations")
