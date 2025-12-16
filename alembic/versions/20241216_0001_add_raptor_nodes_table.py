"""
添加 RAPTOR 节点表

存储 RAPTOR 索引树的节点信息，包括原始 Chunks（叶子节点）和摘要节点。

Revision ID: 20241216_0001
Revises: f8c3e2b1a5d4
Create Date: 2024-12-16 11:30:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# 迁移版本标识
revision: str = "20241216_0001"
down_revision: Union[str, None] = "f8c3e2b1a5d4"  # 依赖 conversation 表迁移
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """升级：创建 raptor_nodes 表"""
    op.create_table(
        "raptor_nodes",
        # 时间戳字段
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        # 主键
        sa.Column("id", sa.String(length=36), nullable=False),
        # 关联字段
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("knowledge_base_id", sa.String(length=36), nullable=False),
        sa.Column("chunk_id", sa.String(length=36), nullable=True),  # 仅叶子节点有值
        # 节点内容
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("level", sa.Integer(), nullable=False, default=0),  # 层级：0=叶子节点
        # 树结构
        sa.Column("parent_id", sa.String(length=36), nullable=True),  # 父节点 ID
        sa.Column("children_ids", sa.JSON(), nullable=True, default=list),  # 子节点 ID 列表
        # 向量索引
        sa.Column("vector_id", sa.String(length=128), nullable=True),
        sa.Column("indexing_status", sa.String(length=20), nullable=False, default="pending"),
        sa.Column("indexing_error", sa.Text(), nullable=True),
        # 元数据
        sa.Column("metadata", sa.JSON(), nullable=True, default=dict),
        # 主键约束
        sa.PrimaryKeyConstraint("id"),
        # 外键约束
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["knowledge_base_id"], ["knowledge_bases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["chunk_id"], ["chunks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_id"], ["raptor_nodes.id"], ondelete="CASCADE"),
    )
    
    # 创建索引
    op.create_index("ix_raptor_nodes_tenant_id", "raptor_nodes", ["tenant_id"])
    op.create_index("ix_raptor_nodes_knowledge_base_id", "raptor_nodes", ["knowledge_base_id"])
    op.create_index("ix_raptor_nodes_chunk_id", "raptor_nodes", ["chunk_id"])
    op.create_index("ix_raptor_nodes_level", "raptor_nodes", ["level"])
    op.create_index("ix_raptor_nodes_parent_id", "raptor_nodes", ["parent_id"])
    op.create_index("ix_raptor_nodes_indexing_status", "raptor_nodes", ["indexing_status"])


def downgrade() -> None:
    """降级：删除 raptor_nodes 表"""
    op.drop_index("ix_raptor_nodes_indexing_status", table_name="raptor_nodes")
    op.drop_index("ix_raptor_nodes_parent_id", table_name="raptor_nodes")
    op.drop_index("ix_raptor_nodes_level", table_name="raptor_nodes")
    op.drop_index("ix_raptor_nodes_chunk_id", table_name="raptor_nodes")
    op.drop_index("ix_raptor_nodes_knowledge_base_id", table_name="raptor_nodes")
    op.drop_index("ix_raptor_nodes_tenant_id", table_name="raptor_nodes")
    op.drop_table("raptor_nodes")
