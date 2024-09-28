"""create divice emane

Revision ID: 8c1a30c0bade
Revises: 756ab0ade12a
Create Date: 2024-09-19 09:04:44.915696

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8c1a30c0bade'
down_revision = '756ab0ade12a'
branch_labels = None
depends_on = None


def upgrade():
    # 在 devices 資料表中新增 ename 欄位
    op.add_column('devices', sa.Column('ename', sa.String(length=100), nullable=False, server_default=''))


def downgrade():
    # 移除 devices 資料表中的 ename 欄位
    op.drop_column('devices', 'ename')
