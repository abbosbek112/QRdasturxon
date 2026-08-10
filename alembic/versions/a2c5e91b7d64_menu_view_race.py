"""menu view race

Revision ID: a2c5e91b7d64
Revises: f6b12d4a7c08
Create Date: 2026-08-09 13:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a2c5e91b7d64'
down_revision: Union[str, Sequence[str], None] = 'f6b12d4a7c08'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Statistikadagi poygani yopadi.

    Eski `UNIQUE(restaurant_id, item_id, day)` menyu qatorini (item_id NULL)
    HIMOYA QILMAGAN: SQL'da NULL != NULL. Bir vaqtda kelgan ikki mijoz
    ikkita qator yasab qo'yardi va shundan keyin har bir ochilish ikkalasini
    ham oshirib, son ikki barobar shishardi.

    Uning o'rniga ikkita qisman indeks qo'yiladi — biri menyu qatori uchun,
    ikkinchisi taom qatorlari uchun. Shundan keyin `ON CONFLICT` ikkala
    holatda ham ishlaydi va poyga umuman qolmaydi.
    """
    # 1. Mavjud takroriy qatorlarni birlashtiramiz — aks holda yangi indeks
    #    qurilmaydi. Sonlar yig'iladi, ya'ni tarix yo'qolmaydi.
    op.execute(
        """
        UPDATE menu_views SET count = (
            SELECT SUM(other.count) FROM menu_views AS other
            WHERE other.restaurant_id = menu_views.restaurant_id
              AND other.day = menu_views.day
              AND (
                    (other.item_id IS NULL AND menu_views.item_id IS NULL)
                 OR other.item_id = menu_views.item_id
              )
        )
        WHERE id IN (
            SELECT MIN(id) FROM menu_views GROUP BY restaurant_id, item_id, day
        )
        """
    )
    op.execute(
        """
        DELETE FROM menu_views WHERE id NOT IN (
            SELECT MIN(id) FROM menu_views GROUP BY restaurant_id, item_id, day
        )
        """
    )

    # 2. Eski cheklovni olib tashlaymiz. SQLite ALTER bilan cheklov o'chira
    #    olmaydi — Alembic uni nusxa-ko'chir usuli bilan aylanib o'tadi.
    with op.batch_alter_table("menu_views") as batch:
        batch.drop_constraint("uq_menu_views_day", type_="unique")

    # 3. Qisman indekslar
    op.create_index(
        "uq_menu_views_menu",
        "menu_views",
        ["restaurant_id", "day"],
        unique=True,
        sqlite_where=sa.text("item_id IS NULL"),
        postgresql_where=sa.text("item_id IS NULL"),
    )
    op.create_index(
        "uq_menu_views_item",
        "menu_views",
        ["restaurant_id", "item_id", "day"],
        unique=True,
        sqlite_where=sa.text("item_id IS NOT NULL"),
        postgresql_where=sa.text("item_id IS NOT NULL"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("uq_menu_views_item", table_name="menu_views")
    op.drop_index("uq_menu_views_menu", table_name="menu_views")
    with op.batch_alter_table("menu_views") as batch:
        batch.create_unique_constraint(
            "uq_menu_views_day", ["restaurant_id", "item_id", "day"]
        )
