"""Add ACVPU consciousness level and supplemental oxygen to the vital signs (NEWS2).

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-30 16:16:41.554570
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0002'
down_revision: Union[str, None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('anlik_vitaller', sa.Column('bilinc', sa.String(length=1), server_default='A', nullable=False))
    op.add_column('anlik_vitaller', sa.Column('ek_oksijen', sa.Boolean(), server_default=sa.text('false'), nullable=False))
    op.create_check_constraint('ck_vit_bilinc', 'anlik_vitaller', "bilinc IN ('A', 'C', 'V', 'P', 'U')")


def downgrade() -> None:
    op.drop_constraint('ck_vit_bilinc', 'anlik_vitaller', type_='check')
    op.drop_column('anlik_vitaller', 'ek_oksijen')
    op.drop_column('anlik_vitaller', 'bilinc')
