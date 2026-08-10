"""zones and waiter areas

Revision ID: e4a90c2b81f3
Revises: d1f8b3c60e57
Create Date: 2026-08-09 10:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e4a90c2b81f3'
down_revision: Union[str, Sequence[str], None] = 'd1f8b3c60e57'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Zal bo'limlari, o'tirish joyi turi va afitsant biriktirishlari.

    Mavjud stollar bo'limsiz va `stol` turida qoladi — ya'ni hozirgi
    restoranlarda hech narsa o'zgarmaydi va chop etilgan QR kodlar
    o'z holicha ishlayveradi.
    """
    op.create_table(
        "zones",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("restaurant_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["restaurant_id"], ["restaurants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("restaurant_id", "name", name="uq_zones_name"),
    )
    op.create_index(op.f("ix_zones_restaurant_id"), "zones", ["restaurant_id"])

    # `batch_alter_table` shart: SQLite mavjud jadvalga tashqi kalit
    # QO'SHA OLMAYDI va Alembic uni nusxa-ko'chir usuli bilan aylanib o'tadi.
    # Postgres'da bu oddiy ALTER bo'lib qoladi.
    #
    # Zona o'chirilsa stol qolaveradi — chop etilgan QR kodi omon qolsin.
    with op.batch_alter_table("tables") as batch:
        batch.add_column(sa.Column("zone_id", sa.Integer(), nullable=True))
        batch.add_column(
            sa.Column(
                "kind",
                sa.Enum("stol", "xona", "divan", "vip", name="tablekind", native_enum=False),
                nullable=False,
                server_default="stol",
            )
        )
        batch.create_foreign_key(
            "fk_tables_zone_id", "zones", ["zone_id"], ["id"], ondelete="SET NULL"
        )
    op.create_index(op.f("ix_tables_zone_id"), "tables", ["zone_id"])

    # Buyurtmadagi nusxa: stol o'chirilsa ham taxtada turi ko'rinib tursin
    op.add_column(
        "orders",
        sa.Column("table_kind", sa.String(length=16), nullable=False, server_default="stol"),
    )

    op.create_table(
        "waiter_zones",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("zone_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["zone_id"], ["zones.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "zone_id"),
    )
    op.create_table(
        "waiter_tables",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("table_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["table_id"], ["tables.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "table_id"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("waiter_tables")
    op.drop_table("waiter_zones")

    op.drop_column("orders", "table_kind")

    op.drop_index(op.f("ix_tables_zone_id"), table_name="tables")
    with op.batch_alter_table("tables") as batch:
        batch.drop_constraint("fk_tables_zone_id", type_="foreignkey")
        batch.drop_column("kind")
        batch.drop_column("zone_id")

    op.drop_index(op.f("ix_zones_restaurant_id"), table_name="zones")
    op.drop_table("zones")
