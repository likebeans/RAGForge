"""add extraction_schemas table

Revision ID: 20250204_0001
Revises: 20250126_0001
Create Date: 2026-02-04

用于 PDF 字段提取到 Excel 功能的提取模板表。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '20250204_0001'
down_revision: Union[str, None] = '20250126_0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'extraction_schemas',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('tenant_id', sa.String(36), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('knowledge_base_id', sa.String(36), sa.ForeignKey('knowledge_bases.id'), nullable=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('fields', sa.JSON, nullable=False, default=list),
        sa.Column('source_filename', sa.String(255), nullable=True),
        sa.Column('usage_count', sa.String(36), default='0'),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_extraction_schemas_tenant_id', 'extraction_schemas', ['tenant_id'])
    op.create_index('ix_extraction_schemas_kb_id', 'extraction_schemas', ['knowledge_base_id'])


def downgrade() -> None:
    op.drop_index('ix_extraction_schemas_kb_id', 'extraction_schemas')
    op.drop_index('ix_extraction_schemas_tenant_id', 'extraction_schemas')
    op.drop_table('extraction_schemas')
