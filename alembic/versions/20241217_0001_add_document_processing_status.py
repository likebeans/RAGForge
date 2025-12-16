"""add document processing_status field

Revision ID: 20241217_0001
Revises: 20241216_0002_add_document_processing_log
Create Date: 2024-12-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20241217_0001'
down_revision: Union[str, None] = '20241216_0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 添加 processing_status 字段，默认值为 'pending'
    # 状态值：pending, processing, completed, failed, interrupted
    op.add_column('documents', sa.Column('processing_status', sa.String(20), nullable=False, server_default='pending'))
    
    # 为 processing_status 字段创建索引，便于查询处理中的文档
    op.create_index('ix_documents_processing_status', 'documents', ['processing_status'])
    
    # 将已有文档（有 chunk_count > 0）的状态设置为 completed
    op.execute("""
        UPDATE documents 
        SET processing_status = 'completed' 
        WHERE (SELECT COUNT(*) FROM chunks WHERE chunks.document_id = documents.id) > 0
    """)


def downgrade() -> None:
    op.drop_index('ix_documents_processing_status', table_name='documents')
    op.drop_column('documents', 'processing_status')
