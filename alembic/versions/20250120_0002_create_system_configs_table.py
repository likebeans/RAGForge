"""
创建 system_configs 表

用于存储系统级配置，支持通过 Admin API 动态修改。

Revision ID: 20250120_0002
Revises: 20250120_0001
Create Date: 2026-01-20
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic
revision = '20250120_0002'
down_revision = '20250120_0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 创建 system_configs 表
    op.create_table(
        'system_configs',
        sa.Column('key', sa.String(100), primary_key=True, nullable=False),
        sa.Column('value', sa.Text, nullable=False),
        sa.Column('description', sa.String(500), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    
    # 创建索引
    op.create_index('ix_system_configs_key', 'system_configs', ['key'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_system_configs_key', table_name='system_configs')
    op.drop_table('system_configs')

