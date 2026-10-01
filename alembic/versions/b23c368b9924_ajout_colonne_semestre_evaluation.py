"""ajout colonne semestre evaluation

Revision ID: b23c368b9924
Revises: 
Create Date: 2026-09-13 09:52:43.082464

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b23c368b9924'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Ajout uniquement de la colonne manquante pour éviter de supprimer les tables existantes
    op.add_column('planification_evaluations', sa.Column('semestre', sa.String(length=50), nullable=True, server_default='Semestre 1'))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('planification_evaluations', 'semestre')