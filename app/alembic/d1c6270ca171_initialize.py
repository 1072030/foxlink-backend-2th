"""initialize

Revision ID: d1c6270ca171
Revises: 
Create Date: 2022-12-04 17:19:20.278907

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd1c6270ca171'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('factory_maps',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('map', sa.JSON(), nullable=False),
    sa.Column('related_devices', sa.JSON(), nullable=False),
    sa.Column('image', sa.LargeBinary(length=5242880), nullable=True),
    sa.Column('created_date', sa.DateTime(timezone=True), nullable=True),
    sa.Column('updated_date', sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_factory_maps_id'), 'factory_maps', ['id'], unique=False)
    op.create_index(op.f('ix_factory_maps_name'), 'factory_maps', ['name'], unique=True)
    op.create_table('shifts',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('shift_beg_time', sa.Time(timezone=True), nullable=False),
    sa.Column('shift_end_time', sa.Time(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_shifts_id'), 'shifts', ['id'], unique=False)
    op.create_table('devices',
    sa.Column('id', sa.String(length=100), nullable=False),
    sa.Column('project', sa.String(length=50), nullable=False),
    sa.Column('process', sa.String(length=50), nullable=True),
    sa.Column('line', sa.Integer(), nullable=True),
    sa.Column('device_name', sa.String(length=20), nullable=False),
    sa.Column('device_cname', sa.String(length=100), nullable=True),
    sa.Column('x_axis', sa.Float(), nullable=False),
    sa.Column('y_axis', sa.Float(), nullable=False),
    sa.Column('is_rescue', sa.Boolean(), nullable=True),
    sa.Column('workshop', sa.Integer(), nullable=True),
    sa.Column('sop_link', sa.String(length=128), nullable=True),
    sa.Column('created_date', sa.DateTime(timezone=True), nullable=True),
    sa.Column('updated_date', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['workshop'], ['factory_maps.id'], name='fk_devices_factory_maps_id_workshop'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_devices_id'), 'devices', ['id'], unique=False)
    op.create_table('users',
    sa.Column('badge', sa.String(length=100), nullable=False),
    sa.Column('username', sa.String(length=50), nullable=False),
    sa.Column('password_hash', sa.String(length=100), nullable=True),
    sa.Column('workshop', sa.Integer(), nullable=True),
    sa.Column('superior', sa.String(length=100), nullable=True),
    sa.Column('level', sa.SmallInteger(), nullable=False),
    sa.Column('shift', sa.Integer(), nullable=True),
    sa.Column('change_pwd', sa.Boolean(), server_default='0', nullable=True),
    sa.Column('current_UUID', sa.String(length=100), nullable=True),
    sa.Column('start_position', sa.String(length=100), nullable=True),
    sa.Column('status', sa.String(length=15), nullable=True),
    sa.Column('at_device', sa.String(length=100), nullable=True),
    sa.Column('shift_start_count', sa.Integer(), nullable=True),
    sa.Column('shift_reject_count', sa.Integer(), nullable=True),
    sa.Column('check_alive_time', sa.DateTime(timezone=True), nullable=True),
    sa.Column('shift_beg_date', sa.DateTime(timezone=True), nullable=True),
    sa.Column('finish_event_date', sa.DateTime(timezone=True), nullable=True),
    sa.Column('login_date', sa.DateTime(timezone=True), nullable=True),
    sa.Column('logout_date', sa.DateTime(timezone=True), nullable=True),
    sa.Column('updated_date', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_date', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['at_device'], ['devices.id'], name='fk_users_devices_id_at_device', ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['shift'], ['shifts.id'], name='fk_users_shifts_id_shift'),
    sa.ForeignKeyConstraint(['start_position'], ['devices.id'], name='fk_users_devices_id_start_position', ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['superior'], ['users.badge'], name='fk_users_users_badge_superior'),
    sa.ForeignKeyConstraint(['workshop'], ['factory_maps.id'], name='fk_users_factory_maps_id_workshop', ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('badge')
    )
    op.create_index(op.f('ix_users_badge'), 'users', ['badge'], unique=False)
    op.create_table('whitelist_devices',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('device', sa.String(length=100), nullable=False),
    sa.Column('created_date', sa.DateTime(timezone=True), nullable=True),
    sa.Column('updated_date', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['device'], ['devices.id'], name='fk_whitelist_devices_devices_id_device', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('device')
    )
    op.create_table('audit_log_headers',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('action', sa.String(length=50), nullable=False),
    sa.Column('table_name', sa.String(length=50), nullable=False),
    sa.Column('record_pk', sa.String(length=100), nullable=True),
    sa.Column('user', sa.String(length=100), nullable=True),
    sa.Column('created_date', sa.DateTime(timezone=True), nullable=True),
    sa.Column('description', sa.String(length=256), nullable=True),
    sa.ForeignKeyConstraint(['user'], ['users.badge'], name='fk_audit_log_headers_users_badge_user', ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_audit_log_headers_action'), 'audit_log_headers', ['action'], unique=False)
    op.create_index(op.f('ix_audit_log_headers_id'), 'audit_log_headers', ['id'], unique=False)
    op.create_index(op.f('ix_audit_log_headers_record_pk'), 'audit_log_headers', ['record_pk'], unique=False)
    op.create_index(op.f('ix_audit_log_headers_table_name'), 'audit_log_headers', ['table_name'], unique=False)
    op.create_table('missions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('device', sa.String(length=100), nullable=True),
    sa.Column('worker', sa.String(length=100), nullable=True),
    sa.Column('description', sa.String(length=256), nullable=True),
    sa.Column('is_done', sa.Boolean(), nullable=True),
    sa.Column('is_done_cure', sa.Boolean(), nullable=True),
    sa.Column('is_done_shift', sa.Boolean(), nullable=True),
    sa.Column('is_done_cancel', sa.Boolean(), nullable=True),
    sa.Column('is_done_finish', sa.Boolean(), nullable=True),
    sa.Column('is_lonely', sa.Boolean(), nullable=True),
    sa.Column('is_emergency', sa.Boolean(), nullable=True),
    sa.Column('overtime_level', sa.Integer(), nullable=True),
    sa.Column('notify_send_date', sa.DateTime(), nullable=True),
    sa.Column('notify_recv_date', sa.DateTime(), nullable=True),
    sa.Column('accept_recv_date', sa.DateTime(), nullable=True),
    sa.Column('repair_beg_date', sa.DateTime(), nullable=True),
    sa.Column('repair_end_date', sa.DateTime(), nullable=True),
    sa.Column('created_date', sa.DateTime(timezone=True), nullable=True),
    sa.Column('updated_date', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['device'], ['devices.id'], name='fk_missions_devices_id_device', ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['worker'], ['users.badge'], name='fk_missions_users_badge_worker', ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_missions_id'), 'missions', ['id'], unique=False)
    op.create_table('user_device_levels',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user', sa.String(length=100), nullable=True),
    sa.Column('device', sa.String(length=100), nullable=True),
    sa.Column('level', sa.SmallInteger(), nullable=True),
    sa.Column('created_date', sa.DateTime(timezone=True), nullable=True),
    sa.Column('updated_date', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['device'], ['devices.id'], name='fk_user_device_levels_devices_id_device', ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user'], ['users.badge'], name='fk_user_device_levels_users_badge_user', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('device', 'user', name='uc_user_device_levels_device_user')
    )
    op.create_index(op.f('ix_user_device_levels_id'), 'user_device_levels', ['id'], unique=False)
    op.create_table('whitelistdevices_users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user', sa.String(length=100), nullable=True),
    sa.Column('whitelistdevice', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['user'], ['users.badge'], name='fk_whitelistdevices_users_users_user_badge', onupdate='CASCADE', ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['whitelistdevice'], ['whitelist_devices.id'], name='fk_whitelistdevices_users_whitelist_devices_whitelistdevice_id', onupdate='CASCADE', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('mission_events',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('mission', sa.Integer(), nullable=True),
    sa.Column('event_id', sa.Integer(), nullable=False),
    sa.Column('category', sa.Integer(), nullable=False),
    sa.Column('message', sa.String(length=100), nullable=True),
    sa.Column('host', sa.String(length=50), nullable=False),
    sa.Column('table_name', sa.String(length=50), nullable=False),
    sa.Column('event_beg_date', sa.DateTime(), nullable=True),
    sa.Column('event_end_date', sa.DateTime(), nullable=True),
    sa.Column('created_date', sa.DateTime(timezone=True), nullable=True),
    sa.Column('updated_date', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['mission'], ['missions.id'], name='fk_mission_events_missions_id_mission', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('event_id', 'table_name', 'mission', name='uc_mission_events_event_id_table_name_mission')
    )
    op.create_table('missions_users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user', sa.String(length=100), nullable=True),
    sa.Column('mission', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['mission'], ['missions.id'], name='fk_missions_users_missions_mission_id', onupdate='CASCADE', ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user'], ['users.badge'], name='fk_missions_users_users_user_badge', onupdate='CASCADE', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('missions_users')
    op.drop_table('mission_events')
    op.drop_table('whitelistdevices_users')
    op.drop_index(op.f('ix_user_device_levels_id'), table_name='user_device_levels')
    op.drop_table('user_device_levels')
    op.drop_index(op.f('ix_missions_id'), table_name='missions')
    op.drop_table('missions')
    op.drop_index(op.f('ix_audit_log_headers_table_name'), table_name='audit_log_headers')
    op.drop_index(op.f('ix_audit_log_headers_record_pk'), table_name='audit_log_headers')
    op.drop_index(op.f('ix_audit_log_headers_id'), table_name='audit_log_headers')
    op.drop_index(op.f('ix_audit_log_headers_action'), table_name='audit_log_headers')
    op.drop_table('audit_log_headers')
    op.drop_table('whitelist_devices')
    op.drop_index(op.f('ix_users_badge'), table_name='users')
    op.drop_table('users')
    op.drop_index(op.f('ix_devices_id'), table_name='devices')
    op.drop_table('devices')
    op.drop_index(op.f('ix_shifts_id'), table_name='shifts')
    op.drop_table('shifts')
    op.drop_index(op.f('ix_factory_maps_name'), table_name='factory_maps')
    op.drop_index(op.f('ix_factory_maps_id'), table_name='factory_maps')
    op.drop_table('factory_maps')
    # ### end Alembic commands ###
