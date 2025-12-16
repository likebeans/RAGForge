"""merge_heads

Revision ID: b67ffb501d5d
Revises: 20241209_0001, 20241217_0001
Create Date: 2025-12-16 16:47:22.880655

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b67ffb501d5d'
down_revision: Union[str, None] = ('20241209_0001', '20241217_0001')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
