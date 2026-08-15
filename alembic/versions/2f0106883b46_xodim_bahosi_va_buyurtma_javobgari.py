"""xodim bahosi va buyurtma javobgari

Ikki narsa qo'shiladi.

`orders.handled_by_id` — buyurtmani kim qabul qilgani. Ilgari bu hech
qayerda yozilmasdi va "kim nechta buyurtmaga javob berdi" degan savolga
javob berib bo'lmasdi. Eski buyurtmalarda maydon bo'sh qoladi: ular
qabul qilinganda bu ma'lumot yo'q edi va uni o'ylab topib bo'lmaydi.

`staff_reviews` — egasining xodimga bergan bahosi. Alohida jadval, chunki
baho vaqt bilan ma'noli: uch oy oldin 3 bo'lib bugun 5 bo'lgani o'sishni
ko'rsatadi, ustiga yozib ketilsa bu yo'qolardi.

Ikkala tashqi kalit ham xodim o'chirilganda tarixni saqlaydi
(`SET NULL`) — buyurtma tarixi ishdan ketgan odam bilan birga
o'chib ketmasligi kerak.

Revision ID: 2f0106883b46
Revises: d42246f60ee8
Create Date: 2026-08-15 18:47:49.088668
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "2f0106883b46"
down_revision: Union[str, Sequence[str], None] = "d42246f60ee8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Cheklovga ANIQ nom beriladi: avtomatik nom bilan orqaga qaytarish
# `drop_constraint(None, ...)` ga tushib, migratsiya yiqilardi
FK_HANDLED_BY = "fk_orders_handled_by_id_users"


def upgrade() -> None:
    op.create_table(
        "staff_reviews",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("restaurant_id", sa.Integer(), nullable=False),
        sa.Column("staff_id", sa.Integer(), nullable=False),
        sa.Column("author_id", sa.Integer(), nullable=True),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("note", sa.String(length=280), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["restaurant_id"], ["restaurants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["staff_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("staff_reviews", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_staff_reviews_created_at"), ["created_at"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_staff_reviews_restaurant_id"), ["restaurant_id"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_staff_reviews_staff_id"), ["staff_id"], unique=False
        )

    with op.batch_alter_table("orders", schema=None) as batch_op:
        batch_op.add_column(sa.Column("handled_by_id", sa.Integer(), nullable=True))
        batch_op.create_index(
            batch_op.f("ix_orders_handled_by_id"), ["handled_by_id"], unique=False
        )
        batch_op.create_foreign_key(
            FK_HANDLED_BY, "users", ["handled_by_id"], ["id"], ondelete="SET NULL"
        )


def downgrade() -> None:
    with op.batch_alter_table("orders", schema=None) as batch_op:
        batch_op.drop_constraint(FK_HANDLED_BY, type_="foreignkey")
        batch_op.drop_index(batch_op.f("ix_orders_handled_by_id"))
        batch_op.drop_column("handled_by_id")

    with op.batch_alter_table("staff_reviews", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_staff_reviews_staff_id"))
        batch_op.drop_index(batch_op.f("ix_staff_reviews_restaurant_id"))
        batch_op.drop_index(batch_op.f("ix_staff_reviews_created_at"))
    op.drop_table("staff_reviews")
