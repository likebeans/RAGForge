"""add_tenant_model_configs_table

Revision ID: 20250121_0001
Revises: 20250120_0002
Create Date: 2026-01-21

租户级模型配置表，支持用户配置自己的 Embedding/LLM/Rerank API Key。
"""
from typing import Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '20250121_0001'
down_revision: Union[str, None] = '20250120_0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 创建 tenant_model_configs 表
    op.create_table(
        'tenant_model_configs',
        sa.Column('id', sa.String(36), primary_key=True, default=lambda: str(__import__('uuid').uuid4())),
        sa.Column('tenant_id', sa.String(36), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('config_type', sa.String(20), nullable=False, index=True),
        sa.Column('provider', sa.String(50), nullable=False),
        sa.Column('model', sa.String(100), nullable=True),
        sa.Column('api_key', sa.Text, nullable=True),
        sa.Column('base_url', sa.String(500), nullable=True),
        sa.Column('is_active', sa.Boolean, default=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), onupdate=sa.func.now(), nullable=False),
    )
    
    # 创建索引
    op.create_index('ix_tenant_model_configs_tenant_id', 'tenant_model_configs', ['tenant_id'])
    op.create_index('ix_tenant_model_configs_config_type', 'tenant_model_configs', ['config_type'])
    
    # 添加租户表关联关系（relationship）
    # 注意：relationship 是在 Python 模型中定义的，不需要在数据库层面添加外键


def downgrade() -> None:
    op.drop_index('ix_tenant_model_configs_config_type', table_name='tenant_model_configs')
    op.drop_index('ix_tenant_model_configs_tenant_id', table_name='tenant_model_configs')
    op.drop_table('tenant_model_configs')

