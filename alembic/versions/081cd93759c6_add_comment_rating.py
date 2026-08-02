"""add comment rating

Revision ID: 081cd93759c6
Revises: 396fa62f8f46
Create Date: 2026-08-02 10:09:32.267449

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '081cd93759c6'
down_revision: Union[str, Sequence[str], None] = '396fa62f8f46'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Izohga yulduzli baho.

    server_default kerak: jadvalda allaqachon izohlar bor va NOT NULL ustun
    ularga qiymatsiz qo'shilmaydi. 0 = "baho qo'yilmagan", ya'ni eski izohlar
    o'rtacha bahoni pasaytirmaydi.
    """
    op.add_column(
        "item_comments",
        sa.Column("rating", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("item_comments", "rating")
