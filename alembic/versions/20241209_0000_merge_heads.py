"""merge migration heads

合并两个迁移分支：f8c3e2b1a5d4 和 a03b985e8e23

Revision ID: 20241209_0000
Revises: f8c3e2b1a5d4, a03b985e8e23
Create Date: 2024-12-09
"""

# revision identifiers, used by Alembic.
revision = "20241209_0000"
down_revision = ("f8c3e2b1a5d4", "a03b985e8e23")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
