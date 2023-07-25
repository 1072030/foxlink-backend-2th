"""initialize

Revision ID: 7d403928226d
Revises: 
Create Date: 2023-07-24 12:01:35.694393

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7d403928226d'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('audit_log_headers',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('action', sa.String(length=50), nullable=False),
    sa.Column('user', sa.String(length=30), nullable=True),
    sa.Column('created_date', sa.DateTime(timezone=True), nullable=True),
    sa.Column('description', sa.String(length=256), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_audit_log_headers_action'), 'audit_log_headers', ['action'], unique=False)
    op.create_index(op.f('ix_audit_log_headers_id'), 'audit_log_headers', ['id'], unique=False)
    op.create_index(op.f('ix_audit_log_headers_user'), 'audit_log_headers', ['user'], unique=False)
    op.create_table('env',
    sa.Column('id', sa.String(length=100), nullable=False),
    sa.Column('key', sa.String(length=50), nullable=False),
    sa.Column('value', sa.String(length=50), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_env_id'), 'env', ['id'], unique=False)
    op.create_table('pending_approvals',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('badge', sa.String(length=100), nullable=False),
    sa.Column('username', sa.String(length=50), nullable=False),
    sa.Column('password_hash', sa.String(length=100), nullable=True),
    sa.Column('created_date', sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_pending_approvals_badge'), 'pending_approvals', ['badge'], unique=False)
    op.create_table('projects',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=50), nullable=False),
    sa.Column('created_date', sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('users',
    sa.Column('badge', sa.String(length=100), nullable=False),
    sa.Column('username', sa.String(length=50), nullable=False),
    sa.Column('password_hash', sa.String(length=100), nullable=True),
    sa.Column('change_pwd', sa.Boolean(), server_default='0', nullable=True),
    sa.Column('current_UUID', sa.String(length=100), nullable=True),
    sa.Column('flag', sa.Boolean(), nullable=True),
    sa.Column('login_date', sa.DateTime(timezone=True), nullable=True),
    sa.Column('logout_date', sa.DateTime(timezone=True), nullable=True),
    sa.Column('updated_date', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_date', sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('badge')
    )
    op.create_index(op.f('ix_users_badge'), 'users', ['badge'], unique=False)
    op.create_table('projects_users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user', sa.String(length=100), nullable=True),
    sa.Column('project', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['project'], ['projects.id'], name='fk_projects_users_projects_project_id', onupdate='CASCADE', ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user'], ['users.badge'], name='fk_projects_users_users_user_badge', onupdate='CASCADE', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('projects_users')
    op.drop_index(op.f('ix_users_badge'), table_name='users')
    op.drop_table('users')
    op.drop_table('projects')
    op.drop_index(op.f('ix_pending_approvals_badge'), table_name='pending_approvals')
    op.drop_table('pending_approvals')
    op.drop_index(op.f('ix_env_id'), table_name='env')
    op.drop_table('env')
    op.drop_index(op.f('ix_audit_log_headers_user'), table_name='audit_log_headers')
    op.drop_index(op.f('ix_audit_log_headers_id'), table_name='audit_log_headers')
    op.drop_index(op.f('ix_audit_log_headers_action'), table_name='audit_log_headers')
    op.drop_table('audit_log_headers')
    # ### end Alembic commands ###
