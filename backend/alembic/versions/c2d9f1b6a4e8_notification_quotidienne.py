"""notification quotidienne

Revision ID: c2d9f1b6a4e8
Revises: b8c3f0a7e5d1
Create Date: 2026-07-23 23:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c2d9f1b6a4e8'
down_revision: Union[str, None] = 'b8c3f0a7e5d1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'parametres_officine',
        sa.Column('notification_active', sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        'parametres_officine',
        sa.Column('notification_heure', sa.String(), nullable=False, server_default="08:00"),
    )
    op.add_column(
        'parametres_officine',
        sa.Column('notification_email', sa.String(), nullable=True),
    )
    op.add_column(
        'parametres_officine',
        sa.Column('notification_derniere_envoyee_le', sa.Date(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('parametres_officine', 'notification_derniere_envoyee_le')
    op.drop_column('parametres_officine', 'notification_email')
    op.drop_column('parametres_officine', 'notification_heure')
    op.drop_column('parametres_officine', 'notification_active')
