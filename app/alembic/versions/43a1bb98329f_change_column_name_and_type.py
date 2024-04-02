"""Change column name and type

Revision ID: 43a1bb98329f
Revises: c5ebffa18d6a
Create Date: 2024-03-26 17:08:16.375284

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '43a1bb98329f'
down_revision = '79bcc92c3331'
branch_labels = None
depends_on = None

def upgrade():
    # Change args to project
    # op.alter_column('task', 'args', new_column_name='project', existing_type=sa.Integer(), nullable=False)
    op.create_foreign_key('fk_task_project_id', 'task', 'projects', ['project'], ['id'])

def downgrade():
    # Revert project to args
    op.drop_constraint('fk_task_project_id', 'task', type_='foreignkey')
    op.alter_column('task', 'project', new_column_name='args', existing_type=sa.String(length=50))
