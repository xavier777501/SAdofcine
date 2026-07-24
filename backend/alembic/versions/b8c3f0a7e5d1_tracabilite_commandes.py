"""tracabilite commandes

Revision ID: b8c3f0a7e5d1
Revises: a1b7e4c9d3f2
Create Date: 2026-07-23 22:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b8c3f0a7e5d1'
down_revision: Union[str, None] = 'a1b7e4c9d3f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Section 7.3 (V9) : un instantané JSON par commande "validée" (export
    # PDF/Excel), pas de table enfant relationnelle — cohérent avec
    # ImportLog.erreurs_detail, déjà stocké en JSON texte.
    op.create_table(
        'commandes_validees',
        sa.Column('officine_id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=True),
        sa.Column('format', sa.String(), nullable=False),
        sa.Column('lignes', sa.Text(), nullable=False),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['officine_id'], ['officines.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_commandes_validees_id'), 'commandes_validees', ['id'], unique=False)
    op.create_index(op.f('ix_commandes_validees_officine_id'), 'commandes_validees', ['officine_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_commandes_validees_officine_id'), table_name='commandes_validees')
    op.drop_index(op.f('ix_commandes_validees_id'), table_name='commandes_validees')
    op.drop_table('commandes_validees')
