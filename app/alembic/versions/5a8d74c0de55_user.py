"""User 

Revision ID: 5a8d74c0de55
Revises: afddbd6e5fec
Create Date: 2024-06-19 08:06:52.883101

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5a8d74c0de55'
down_revision = 'afddbd6e5fec'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('users', sa.Column('email', sa.String(length=50), nullable=True))


def downgrade():
    op.drop_column('users', 'email')