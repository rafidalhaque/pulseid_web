"""fix work_policy default to 0

Revision ID: 03a1e73d4760
Revises: 7c0f13de768d
Create Date: 2026-05-14 15:45:01.716503

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '03a1e73d4760'
down_revision = '7c0f13de768d'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('_work_policy', 'late_minutes', server_default='0')
    op.alter_column('_work_policy', 'early_minutes', server_default='0')


def downgrade():
    op.alter_column('_work_policy', 'late_minutes', server_default='15')
    op.alter_column('_work_policy', 'early_minutes', server_default='15')
