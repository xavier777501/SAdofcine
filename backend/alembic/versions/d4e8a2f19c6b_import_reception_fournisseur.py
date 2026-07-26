"""import reception fournisseur

Revision ID: d4e8a2f19c6b
Revises: b8c3f0a7e5d1
Create Date: 2026-07-25 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4e8a2f19c6b'
down_revision: Union[str, None] = 'b8c3f0a7e5d1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Section 4quater (V9) : nom du fournisseur capture a l'import Type 3,
    # a titre indicatif dans l'historique des imports.
    op.add_column(
        'import_logs',
        sa.Column('fournisseur', sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('import_logs', 'fournisseur')
