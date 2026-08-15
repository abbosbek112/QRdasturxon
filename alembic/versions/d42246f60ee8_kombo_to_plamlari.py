"""kombo to'plamlari

Kombo — bir necha taomdan iborat to'plam, birga arzonroq.

Narx `combos` da ALOHIDA turadi va tarkibdan hisoblanmaydi: kombo'ning
butun ma'nosi chegirmada va uni egasi o'zi belgilaydi.

`combo_lines.item_id` CASCADE bilan o'chadi — tarkibida yo'q taom turgan
kombo mijozga yolg'on va'da bo'lardi.

Revision ID: d42246f60ee8
Revises: 5be53d0d8611
Create Date: 2026-08-15 10:21:08.683865
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d42246f60ee8"
down_revision: Union[str, Sequence[str], None] = "5be53d0d8611"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Loyihadagi boshqa i18n ustunlari bilan bir xil: PostgreSQL'da JSONB,
# SQLite'da oddiy JSON
I18N = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")


def upgrade() -> None:
    op.create_table(
        "combos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("restaurant_id", sa.Integer(), nullable=False),
        sa.Column("name", I18N, nullable=False),
        sa.Column("description", I18N, nullable=False),
        sa.Column("price", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("image", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["restaurant_id"], ["restaurants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("combos", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_combos_restaurant_id"), ["restaurant_id"], unique=False
        )

    op.create_table(
        "combo_lines",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("combo_id", sa.Integer(), nullable=False),
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["combo_id"], ["combos.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["item_id"], ["menu_items.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("combo_lines", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_combo_lines_combo_id"), ["combo_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_combo_lines_item_id"), ["item_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("combo_lines", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_combo_lines_item_id"))
        batch_op.drop_index(batch_op.f("ix_combo_lines_combo_id"))
    op.drop_table("combo_lines")

    with op.batch_alter_table("combos", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_combos_restaurant_id"))
    op.drop_table("combos")
