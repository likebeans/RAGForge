"""add document processing_log field

Revision ID: 20241216_0002
Revises: 20241216_0001_add_raptor_nodes_table
Create Date: 2024-12-16

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20241216_0002'
down_revision = '20241216_0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 添加 processing_log 字段到 documents 表
    op.add_column('documents', sa.Column('processing_log', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('documents', 'processing_log')
