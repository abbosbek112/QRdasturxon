"""drop halal marker

Revision ID: c9f2a4b71d06
Revises: b8d3f1a52c04
Create Date: 2026-08-12 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c9f2a4b71d06'
down_revision: Union[str, Sequence[str], None] = 'b8d3f1a52c04'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """"Halol" belgisini olib tashlaydi.

    O'zbekistondagi kafelarda deyarli hamma taom halol, ya'ni bu belgi hech
    narsani ajratmasdi va menyuda shunchaki joy egallardi. Egasi uni har
    taomga qo'yib chiqishga majbur bo'lardi, mijoz esa undan yangi ma'lumot
    olmasdi.

    "O'tkir" va "Vegetarian" qoladi — ular haqiqatan tanlovga ta'sir qiladi.

    SQLite ustunni to'g'ridan-to'g'ri o'chira olmaydi, shuning uchun Alembic
    nusxa-ko'chir usuli bilan aylanib o'tadi.
    """
    with op.batch_alter_table("menu_items") as batch:
        batch.drop_column("is_halal")


def downgrade() -> None:
    """Ustunni qaytaradi, lekin qiymatlar tiklanmaydi — ular o'chib ketgan."""
    with op.batch_alter_table("menu_items") as batch:
        batch.add_column(
            sa.Column("is_halal", sa.Boolean(), nullable=False, server_default=sa.false())
        )
