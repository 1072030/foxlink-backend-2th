"""Update devices table-3

Revision ID: 76c44ab22fe3
Revises: 18ba6992bea1
Create Date: 2024-05-07 04:02:50.053280

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '76c44ab22fe3'
down_revision = '18ba6992bea1'
branch_labels = None
depends_on = None


def upgrade():
    # Add the new column with a default value of False
    op.add_column('devices', sa.Column('retrain', sa.Boolean(), nullable=False, server_default=sa.sql.expression.false()))


def downgrade():
    # Remove the column on downgrade
    op.drop_column('devices', 'retrain')
