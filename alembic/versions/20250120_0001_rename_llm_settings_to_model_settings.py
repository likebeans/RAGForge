"""rename llm_settings to model_settings

Revision ID: 20250120_0001
Revises: 343d21247c23
Create Date: 2025-01-20

将 tenants 表的 llm_settings 字段重命名为 model_settings，
以支持存储更完整的模型配置（包括 Provider API Keys 和默认模型）。
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20250120_0001"
down_revision = "343d21247c23"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 检查 llm_settings 列是否存在，如果存在则重命名为 model_settings
    # 如果 model_settings 已经存在，则跳过
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('tenants')]
    
    if 'llm_settings' in columns and 'model_settings' not in columns:
        op.alter_column(
            'tenants',
            'llm_settings',
            new_column_name='model_settings',
            existing_type=sa.JSON(),
            existing_nullable=True,
        )
    elif 'model_settings' not in columns and 'llm_settings' not in columns:
        # 两个列都不存在，创建 model_settings
        op.add_column(
            'tenants',
            sa.Column('model_settings', sa.JSON(), nullable=True, default=dict),
        )


def downgrade() -> None:
    # 回滚：将 model_settings 重命名回 llm_settings
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('tenants')]
    
    if 'model_settings' in columns and 'llm_settings' not in columns:
        op.alter_column(
            'tenants',
            'model_settings',
            new_column_name='llm_settings',
            existing_type=sa.JSON(),
            existing_nullable=True,
        )
