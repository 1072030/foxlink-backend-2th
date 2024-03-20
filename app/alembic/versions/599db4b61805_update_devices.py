"""update devices

Revision ID: 599db4b61805
Revises: c0192abbc8fc
Create Date: 2024-03-12 20:15:12.242081

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '599db4b61805'
down_revision = 'c0192abbc8fc'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('devices',sa.Column('flag', sa.Boolean(), default=False))
    pass


def downgrade() -> None:
    op.drop_column('devices', 'flag')
    pass
