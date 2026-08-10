"""tables and orders

Revision ID: b3a41c7d5e92
Revises: 92565c21fe2a
Create Date: 2026-08-07 12:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b3a41c7d5e92'
down_revision: Union[str, Sequence[str], None] = '92565c21fe2a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Stollar, buyurtmalar va buyurtma qatorlari.

    `users.role` ga tegilmaydi: ustun VARCHAR(16) va CHECK cheklovi yo'q
    (SQLAlchemy 2.0 da Enum.create_constraint standart False), ya'ni yangi
    "waiter" qiymati mavjud sxemaga o'z-o'zidan sig'adi.
    """
    # Mavjud restoranlar bor, shuning uchun server_default shart
    op.add_column(
        "restaurants",
        sa.Column("orders_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "restaurants",
        sa.Column("order_window_minutes", sa.Integer(), nullable=False, server_default="30"),
    )

    op.create_table(
        "tables",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("restaurant_id", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(length=32), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["restaurant_id"], ["restaurants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("restaurant_id", "label", name="uq_tables_label"),
    )
    op.create_index(op.f("ix_tables_restaurant_id"), "tables", ["restaurant_id"])
    op.create_index(op.f("ix_tables_code"), "tables", ["code"], unique=True)

    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("restaurant_id", sa.Integer(), nullable=False),
        # Stol o'chirilsa buyurtma tarixi qolsin
        sa.Column("table_id", sa.Integer(), nullable=True),
        sa.Column("table_label", sa.String(length=32), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column(
            "status",
            sa.Enum("new", "accepted", "served", "cancelled", name="orderstatus", native_enum=False),
            nullable=False,
        ),
        sa.Column("note", sa.String(length=280), nullable=True),
        sa.Column("total", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("accepted_at", sa.DateTime(), nullable=True),
        sa.Column("closed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["restaurant_id"], ["restaurants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["table_id"], ["tables.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_orders_restaurant_id"), "orders", ["restaurant_id"])
    op.create_index(op.f("ix_orders_code"), "orders", ["code"], unique=True)
    op.create_index(op.f("ix_orders_status"), "orders", ["status"])
    op.create_index(op.f("ix_orders_created_at"), "orders", ["created_at"])

    op.create_table(
        "order_lines",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        # Taom menyudan o'chirilsa ham qator nomi va narxi bilan qoladi
        sa.Column("item_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("unit_price", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["item_id"], ["menu_items.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_order_lines_order_id"), "order_lines", ["order_id"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_order_lines_order_id"), table_name="order_lines")
    op.drop_table("order_lines")

    op.drop_index(op.f("ix_orders_created_at"), table_name="orders")
    op.drop_index(op.f("ix_orders_status"), table_name="orders")
    op.drop_index(op.f("ix_orders_code"), table_name="orders")
    op.drop_index(op.f("ix_orders_restaurant_id"), table_name="orders")
    op.drop_table("orders")

    op.drop_index(op.f("ix_tables_code"), table_name="tables")
    op.drop_index(op.f("ix_tables_restaurant_id"), table_name="tables")
    op.drop_table("tables")

    op.drop_column("restaurants", "order_window_minutes")
    op.drop_column("restaurants", "orders_enabled")
