"""ajustement manuel commande

Revision ID: f3a7c9d21b6e
Revises: dfb0d2952f72
Create Date: 2026-07-15 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f3a7c9d21b6e'
down_revision: Union[str, None] = 'dfb0d2952f72'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('references', sa.Column('qte_a_commander_override', sa.Float(), nullable=True))
    op.add_column('references', sa.Column('inclusion_manuelle', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('references', 'inclusion_manuelle')
    op.drop_column('references', 'qte_a_commander_override')
