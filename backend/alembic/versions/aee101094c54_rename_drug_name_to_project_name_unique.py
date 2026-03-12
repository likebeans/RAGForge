"""rename_drug_name_to_project_name_unique

Revision ID: aee101094c54
Revises: 780c9bebab2e
Create Date: 2026-03-12 17:27:14.002994

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'aee101094c54'
down_revision: Union[str, None] = '780c9bebab2e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 重命名列（保留数据）
    op.alter_column('project_master', 'drug_name', new_column_name='project_name')
    # 删除旧索引
    op.drop_index(op.f('ix_project_master_drug_name'), table_name='project_master')
    # 添加唯一索引
    op.create_index(op.f('ix_project_master_project_name'), 'project_master', ['project_name'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_project_master_project_name'), table_name='project_master')
    op.create_index(op.f('ix_project_master_drug_name'), 'project_master', ['drug_name'], unique=False)
    op.alter_column('project_master', 'project_name', new_column_name='drug_name')
