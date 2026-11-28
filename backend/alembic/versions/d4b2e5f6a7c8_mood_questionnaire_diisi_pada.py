"""mood_questionnaire: kolom diisi_pada (jam kuesioner diisi, untuk dataset model personalisasi)

Revision ID: d4b2e5f6a7c8
Revises: c3a1d2e4f5b6
Create Date: 2026-11-22 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd4b2e5f6a7c8'
down_revision: Union[str, None] = 'c3a1d2e4f5b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('mood_questionnaire', sa.Column('diisi_pada', sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column('mood_questionnaire', 'diisi_pada')
