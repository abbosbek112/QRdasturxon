"""two plans with yearly billing

Revision ID: 8707209aa810
Revises: cfc6216f7469
Create Date: 2026-07-31 17:33:19.173945

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8707209aa810'
down_revision: Union[str, Sequence[str], None] = 'cfc6216f7469'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# SQLAlchemy 2.0 da native_enum=False bo'lgan Enum uchun CHECK cheklovi
# yaratilmaydi (create_constraint standart holda False) — bazada ustun oddiy
# VARCHAR bo'lib turadi. Shuning uchun bu yerda faqat ma'lumot ko'chiriladi,
# cheklov bilan ovora bo'lish kerak emas.


OLD_PLAN = sa.Enum("free", "standard", "premium", name="plan", native_enum=False)
NEW_PLAN = sa.Enum("free", "full", name="plan", native_enum=False)


def upgrade() -> None:
    """Uchta tarifni ikkitaga birlashtiradi: standard va premium -> full.

    Avval ma'lumot ko'chiriladi, keyin ustun eni toraytiriladi — teskari
    tartibda 'standard' (8 belgi) yangi enga sig'may qolardi.
    """
    op.execute(
        "UPDATE restaurants SET plan = 'full' WHERE plan IN ('standard', 'premium')"
    )
    with op.batch_alter_table("restaurants", schema=None) as batch_op:
        batch_op.alter_column(
            "plan",
            existing_type=OLD_PLAN,
            type_=NEW_PLAN,
            existing_nullable=False,
            existing_server_default=sa.text("'free'"),
        )


def downgrade() -> None:
    """'full' avval qaysi biri bo'lganini bilib bo'lmaydi — hammasi 'standard'."""
    with op.batch_alter_table("restaurants", schema=None) as batch_op:
        batch_op.alter_column(
            "plan",
            existing_type=NEW_PLAN,
            type_=OLD_PLAN,
            existing_nullable=False,
            existing_server_default=sa.text("'free'"),
        )
    op.execute("UPDATE restaurants SET plan = 'standard' WHERE plan = 'full'")
