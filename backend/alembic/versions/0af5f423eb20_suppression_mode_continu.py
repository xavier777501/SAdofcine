"""suppression mode continu

Le cahier des charges (V3) ne donne une formule de quantité à commander que
pour le cycle périodique (décade/mensuel, section 6.5). Le mode continu
n'avait qu'une formule improvisée côté backend, jamais validée contre le
fichier Excel de référence. Retiré : seuls décade (10j) et mensuel (30j)
restent des rythmes de commande valides.

Revision ID: 0af5f423eb20
Revises: f3a7c9d21b6e
Create Date: 2026-07-16 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0af5f423eb20'
down_revision: Union[str, None] = 'f3a7c9d21b6e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Bascule toute officine restée en mode continu (0) sur décade (10),
    # le rythme par défaut de l'application.
    op.execute("UPDATE parametres_officine SET cycle_commande_jours = 10 WHERE cycle_commande_jours = 0")
    op.drop_column('references', 'qte_commander_continu')


def downgrade() -> None:
    op.add_column('references', sa.Column('qte_commander_continu', sa.Float(), nullable=True))
