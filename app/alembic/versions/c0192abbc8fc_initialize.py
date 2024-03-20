"""initialize

Revision ID: c0192abbc8fc
Revises: 
Create Date: 2024-02-18 07:56:34.301661

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c0192abbc8fc'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('env',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('key', sa.String(length=50), nullable=False),
    sa.Column('value', sa.String(length=50), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
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
    sa.Column('current_UUID', sa.String(length=100), nullable=True),
    sa.Column('flag', sa.Boolean(), nullable=True),
    sa.Column('login_date', sa.DateTime(timezone=True), nullable=True),
    sa.Column('logout_date', sa.DateTime(timezone=True), nullable=True),
    sa.Column('updated_date', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_date', sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('badge')
    )
    op.create_index(op.f('ix_users_badge'), 'users', ['badge'], unique=False)
    op.create_table('audit_log_headers',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('action', sa.String(length=50), nullable=False),
    sa.Column('user', sa.String(length=100), nullable=True),
    sa.Column('created_date', sa.DateTime(timezone=True), nullable=True),
    sa.Column('description', sa.String(length=256), nullable=True),
    sa.ForeignKeyConstraint(['user'], ['users.badge'], name='fk_audit_log_headers_users_badge_user', ondelete='NO ACTION'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_audit_log_headers_action'), 'audit_log_headers', ['action'], unique=False)
    op.create_index(op.f('ix_audit_log_headers_id'), 'audit_log_headers', ['id'], unique=False)
    op.create_table('devices',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('line', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('cname', sa.String(length=100), nullable=False),
    sa.Column('project', sa.Integer(), nullable=False),
    sa.Column('created_date', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['project'], ['projects.id'], name='fk_devices_projects_id_project', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('project_users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('project', sa.Integer(), nullable=True),
    sa.Column('user', sa.String(length=100), nullable=False),
    sa.Column('permission', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['project'], ['projects.id'], name='fk_project_users_projects_id_project', ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user'], ['users.badge'], name='fk_project_users_users_badge_user'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('aoi_measures',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('device', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('created_date', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['device'], ['devices.id'], name='fk_aoi_measures_devices_id_device', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_aoi_measures_name'), 'aoi_measures', ['name'], unique=False)
    op.create_table('project_events',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('device', sa.Integer(), nullable=True),
    sa.Column('name', sa.String(length=50), nullable=False),
    sa.Column('category', sa.Integer(), nullable=True),
    sa.Column('created_date', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['device'], ['devices.id'], name='fk_project_events_devices_id_device', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('aoi_feature',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('date', sa.DateTime(timezone=True), nullable=False),
    sa.Column('operation_day', sa.Boolean(), nullable=True),
    sa.Column('pcs', sa.Integer(), nullable=True),
    sa.Column('ng_num', sa.Integer(), nullable=True),
    sa.Column('ng_rate', sa.Float(), nullable=True),
    sa.Column('ct_max', sa.Float(), nullable=True),
    sa.Column('ct_mean', sa.Float(), nullable=True),
    sa.Column('ct_min', sa.Float(), nullable=True),
    sa.Column('device', sa.Integer(), nullable=False),
    sa.Column('aoi_measure', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['aoi_measure'], ['aoi_measures.id'], name='fk_aoi_feature_aoi_measures_id_aoi_measure', ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['device'], ['devices.id'], name='fk_aoi_feature_devices_id_device', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('dn_mf',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('date', sa.DateTime(timezone=True), nullable=False),
    sa.Column('shift', sa.String(length=100), nullable=False),
    sa.Column('pcs', sa.Integer(), nullable=True),
    sa.Column('operation_time', sa.Time(), nullable=True),
    sa.Column('device', sa.Integer(), nullable=False),
    sa.Column('aoi_measure', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['aoi_measure'], ['aoi_measures.id'], name='fk_dn_mf_aoi_measures_id_aoi_measure', ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['device'], ['devices.id'], name='fk_dn_mf_devices_id_device', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_dn_mf_shift'), 'dn_mf', ['shift'], unique=False)
    op.create_table('error_feature',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('date', sa.DateTime(timezone=True), nullable=False),
    sa.Column('project', sa.Integer(), nullable=False),
    sa.Column('device', sa.Integer(), nullable=False),
    sa.Column('event', sa.Integer(), nullable=False),
    sa.Column('operation_day', sa.Boolean(), nullable=True),
    sa.Column('happened', sa.Integer(), nullable=True),
    sa.Column('dur_max', sa.Integer(), nullable=True),
    sa.Column('dur_mean', sa.Float(), nullable=True),
    sa.Column('dur_min', sa.Integer(), nullable=True),
    sa.Column('last_time_max', sa.Integer(), nullable=True),
    sa.Column('last_time_mean', sa.Float(), nullable=True),
    sa.Column('last_time_min', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['device'], ['devices.id'], name='fk_error_feature_devices_id_device', ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['event'], ['project_events.id'], name='fk_error_feature_project_events_id_event', ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['project'], ['projects.id'], name='fk_error_feature_projects_id_project', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('hourly_mf',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('date', sa.DateTime(timezone=True), nullable=False),
    sa.Column('hour', sa.Integer(), nullable=False),
    sa.Column('shift', sa.String(length=100), nullable=False),
    sa.Column('pcs', sa.Integer(), nullable=True),
    sa.Column('ng_num', sa.Integer(), nullable=True),
    sa.Column('ng_rate', sa.Float(), nullable=True),
    sa.Column('first_prod_time', sa.DateTime(), nullable=True),
    sa.Column('last_prod_time', sa.DateTime(), nullable=True),
    sa.Column('operation_time', sa.Time(), nullable=True),
    sa.Column('device', sa.Integer(), nullable=False),
    sa.Column('aoi_measure', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['aoi_measure'], ['aoi_measures.id'], name='fk_hourly_mf_aoi_measures_id_aoi_measure', ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['device'], ['devices.id'], name='fk_hourly_mf_devices_id_device', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_hourly_mf_shift'), 'hourly_mf', ['shift'], unique=False)
    op.create_table('pred_targets',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('device', sa.Integer(), nullable=False),
    sa.Column('event', sa.Integer(), nullable=False),
    sa.Column('target', sa.Boolean(), nullable=True),
    sa.ForeignKeyConstraint(['device'], ['devices.id'], name='fk_pred_targets_devices_id_device', ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['event'], ['project_events.id'], name='fk_pred_targets_project_events_id_event', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('predict_results',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('device', sa.Integer(), nullable=False),
    sa.Column('event', sa.Integer(), nullable=False),
    sa.Column('pred', sa.String(length=100), nullable=False),
    sa.Column('ori_date', sa.DateTime(timezone=True), nullable=False),
    sa.Column('pred_date', sa.DateTime(timezone=True), nullable=False),
    sa.Column('pred_type', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['device'], ['devices.id'], name='fk_predict_results_devices_id_device', ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['event'], ['project_events.id'], name='fk_predict_results_project_events_id_event', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_predict_results_pred'), 'predict_results', ['pred'], unique=False)
    op.create_table('train_performances',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('device', sa.Integer(), nullable=False),
    sa.Column('event', sa.Integer(), nullable=False),
    sa.Column('threshold', sa.Float(), nullable=True),
    sa.Column('actual_cutpoint', sa.Integer(), nullable=True),
    sa.Column('arf', sa.Float(), nullable=True),
    sa.Column('acc', sa.Float(), nullable=True),
    sa.Column('red_recall', sa.Float(), nullable=True),
    sa.Column('red_f1score', sa.Float(), nullable=True),
    sa.Column('used_col', sa.Text(), nullable=False),
    sa.Column('freq', sa.String(length=100), nullable=False),
    sa.Column('created_date', sa.String(length=100), nullable=False),
    sa.ForeignKeyConstraint(['device'], ['devices.id'], name='fk_train_performances_devices_id_device', ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['event'], ['project_events.id'], name='fk_train_performances_project_events_id_event', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_train_performances_created_date'), 'train_performances', ['created_date'], unique=False)
    op.create_index(op.f('ix_train_performances_freq'), 'train_performances', ['freq'], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_train_performances_freq'), table_name='train_performances')
    op.drop_index(op.f('ix_train_performances_created_date'), table_name='train_performances')
    op.drop_table('train_performances')
    op.drop_index(op.f('ix_predict_results_pred'), table_name='predict_results')
    op.drop_table('predict_results')
    op.drop_table('pred_targets')
    op.drop_index(op.f('ix_hourly_mf_shift'), table_name='hourly_mf')
    op.drop_table('hourly_mf')
    op.drop_table('error_feature')
    op.drop_index(op.f('ix_dn_mf_shift'), table_name='dn_mf')
    op.drop_table('dn_mf')
    op.drop_table('aoi_feature')
    op.drop_table('project_events')
    op.drop_index(op.f('ix_aoi_measures_name'), table_name='aoi_measures')
    op.drop_table('aoi_measures')
    op.drop_table('project_users')
    op.drop_table('devices')
    op.drop_index(op.f('ix_audit_log_headers_id'), table_name='audit_log_headers')
    op.drop_index(op.f('ix_audit_log_headers_action'), table_name='audit_log_headers')
    op.drop_table('audit_log_headers')
    op.drop_index(op.f('ix_users_badge'), table_name='users')
    op.drop_table('users')
    op.drop_table('projects')
    op.drop_table('env')
    # ### end Alembic commands ###
