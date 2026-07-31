"""add menu item ingredients

Revision ID: 4009b2b96973
Revises: 4380d943da2c
Create Date: 2026-07-31 10:47:29.851499

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4009b2b96973'
down_revision: Union[str, Sequence[str], None] = '4380d943da2c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # server_default mavjud qatorlarga bo'sh lug'at beradi — usiz NOT NULL buziladi
    with op.batch_alter_table("menu_items", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("ingredients", sa.JSON(), nullable=False, server_default="{}")
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("menu_items", schema=None) as batch_op:
        batch_op.drop_column("ingredients")
