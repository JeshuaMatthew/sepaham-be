"""add_onboarding_system_tables

Revision ID: 9eca0fe13df8
Revises: e73a1d9c2841
Create Date: 2026-09-27 11:21:47.918421

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9eca0fe13df8'
down_revision: Union[str, Sequence[str], None] = 'e73a1d9c2841'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
