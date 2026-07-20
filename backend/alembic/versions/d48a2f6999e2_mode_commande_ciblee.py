"""mode commande ciblee

Revision ID: d48a2f6999e2
Revises: 0af5f423eb20
Create Date: 2026-07-20 21:32:25.599226

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd48a2f6999e2'
down_revision: Union[str, None] = '0af5f423eb20'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # server_default requis : ADD COLUMN ... NOT NULL sur une table déjà
    # peuplée (officines existantes) doit fournir une valeur pour les lignes
    # existantes, contrairement aux migrations précédentes qui ne créaient
    # que des tables neuves.
    op.add_column(
        'parametres_officine',
        sa.Column('mode_commande_ciblee', sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        'references',
        sa.Column('dans_dernier_import_commande', sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column('references', 'dans_dernier_import_commande')
    op.drop_column('parametres_officine', 'mode_commande_ciblee')
