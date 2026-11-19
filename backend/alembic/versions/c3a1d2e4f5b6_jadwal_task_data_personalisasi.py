"""jadwal_task: kolom data model personalisasi (dipindah, eksplorasi, fitur)

Status baru `tidak_diketahui` tidak butuh perubahan skema (status = varchar(20) biasa).

Revision ID: c3a1d2e4f5b6
Revises: bc925661c16c
Create Date: 2026-11-19 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c3a1d2e4f5b6'
down_revision: Union[str, None] = 'bc925661c16c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('jadwal_task', sa.Column('dipindah', sa.Boolean(), server_default=sa.false(), nullable=False))
    op.add_column('jadwal_task', sa.Column('eksplorasi', sa.Boolean(), server_default=sa.false(), nullable=False))
    op.add_column('jadwal_task', sa.Column('fitur', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('jadwal_task', 'fitur')
    op.drop_column('jadwal_task', 'eksplorasi')
    op.drop_column('jadwal_task', 'dipindah')
