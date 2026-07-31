"""themes and prep time

Revision ID: 396fa62f8f46
Revises: 0249101dc267
Create Date: 2026-07-31 18:15:33.588127

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '396fa62f8f46'
down_revision: Union[str, Sequence[str], None] = '0249101dc267'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # server_default bo'lmasa mavjud qatorlarda NOT NULL buziladi
    with op.batch_alter_table("menu_items", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("prep_minutes", sa.Integer(), nullable=False, server_default="0")
        )

    with op.batch_alter_table("restaurants", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "theme", sa.String(length=32), nullable=False, server_default="zamonaviy"
            )
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("restaurants", schema=None) as batch_op:
        batch_op.drop_column("theme")

    with op.batch_alter_table("menu_items", schema=None) as batch_op:
        batch_op.drop_column("prep_minutes")
