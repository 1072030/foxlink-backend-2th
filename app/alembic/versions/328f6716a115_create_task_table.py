"""create task table

Revision ID: 328f6716a115
Revises: 599db4b61805
Create Date: 2024-03-13 17:35:24.504653

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '328f6716a115'
down_revision = '599db4b61805'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'task',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('action', sa.String(50), nullable=False),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('args', sa.String(50), nullable=False),
        sa.Column('updated_date', sa.DateTime(), nullable=False),
        sa.Column('created_date', sa.DateTime(), nullable=False)
    )
    pass


def downgrade() -> None:
    op.drop_table('task')
    pass
