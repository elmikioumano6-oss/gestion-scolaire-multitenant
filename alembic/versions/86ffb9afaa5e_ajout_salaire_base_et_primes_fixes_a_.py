"""ajout salaire_base et primes_fixes a users

Revision ID: 86ffb9afaa5e
Revises: b23c368b9924
Create Date: 2026-09-24 18:10:58.154940

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '86ffb9afaa5e'
down_revision: Union[str, Sequence[str], None] = 'b23c368b9924'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Ajout sécurisé des colonnes sans supprimer aucune table
    op.add_column('users', sa.Column('salaire_base', sa.Float(), nullable=True, server_default='0.0'))
    op.add_column('users', sa.Column('primes_fixes', sa.Float(), nullable=True, server_default='0.0'))
    
    op.add_column('enseignants', sa.Column('salaire_base', sa.Float(), nullable=True, server_default='0.0'))
    op.add_column('enseignants', sa.Column('taux_horaire', sa.Float(), nullable=True, server_default='0.0'))


def downgrade() -> None:
    """Downgrade schema."""
    # Suppression des colonnes en cas de retour arrière
    op.drop_column('enseignants', 'taux_horaire')
    op.drop_column('enseignants', 'salaire_base')
    op.drop_column('users', 'primes_fixes')
    op.drop_column('users', 'salaire_base')