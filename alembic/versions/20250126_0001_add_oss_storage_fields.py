"""add oss storage fields

Revision ID: 20250126_0001
Revises: 20250121_0001
Create Date: 2026-01-26 09:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20250126_0001'
down_revision: Union[str, None] = '20250121_0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 添加原始文件 OSS 路径字段
    op.add_column('documents', sa.Column('raw_file_path', sa.String(500), nullable=True))
    
    # 添加解析结果 OSS 路径字段
    op.add_column('documents', sa.Column('parsed_result_path', sa.String(500), nullable=True))


def downgrade() -> None:
    op.drop_column('documents', 'parsed_result_path')
    op.drop_column('documents', 'raw_file_path')
