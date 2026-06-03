"""add is_current to experiences and educations

Revision ID: a1f4c7e9d2b8
Revises: c6856a75cd09
Create Date: 2026-06-03 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1f4c7e9d2b8'
down_revision: Union[str, Sequence[str], None] = 'c6856a75cd09'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'experiences',
        sa.Column('is_current', sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        'educations',
        sa.Column('is_current', sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('educations', 'is_current')
    op.drop_column('experiences', 'is_current')
