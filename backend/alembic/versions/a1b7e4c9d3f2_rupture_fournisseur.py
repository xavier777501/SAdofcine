"""rupture fournisseur

Revision ID: a1b7e4c9d3f2
Revises: d48a2f6999e2
Create Date: 2026-07-23 22:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b7e4c9d3f2'
down_revision: Union[str, None] = 'd48a2f6999e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Section 6.8 (V9) : None = pas en attente. Une date passée redevient
    # inactive par simple comparaison à la volée (pas de job de nettoyage).
    op.add_column(
        'references',
        sa.Column('fournisseur_indisponible_jusqu_au', sa.Date(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('references', 'fournisseur_indisponible_jusqu_au')
