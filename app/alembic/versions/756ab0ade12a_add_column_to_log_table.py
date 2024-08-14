"""add column to log table

Revision ID: 756ab0ade12a
Revises: 8256f5b670ed
Create Date: 2024-08-09 14:47:07.608381

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '756ab0ade12a'
down_revision = '8256f5b670ed'
branch_labels = None
depends_on = None

def upgrade():
    # commands to upgrade the database
    op.add_column('audit_log_headers', sa.Column('project', sa.String(length=50), nullable=True))

def downgrade():
    # commands to downgrade the database
    op.drop_column('audit_log_headers', 'project')