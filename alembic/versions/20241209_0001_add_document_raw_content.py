"""add document raw_content field

Revision ID: 20241209_0001
Revises: f8c3e2b1a5d4
Create Date: 2024-12-09

为 Document 表添加 raw_content 字段，存储原始文件内容，
用于 Ground/Playground 的分块预览功能。
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20241209_0001"
down_revision = "20241209_0000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column("raw_content", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("documents", "raw_content")
