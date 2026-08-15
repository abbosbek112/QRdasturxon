"""kategoriya rasmi

Bo'lim rasmi menyuda kategoriya nomi yonida turadi. Uzun menyuda odam
"Ichimliklar" so'zini o'qishdan ko'ra stakan rasmini tezroq topadi.

Ustun bo'sh qoladi: mavjud kategoriyalarda rasm yo'q va ular ilgarigidek
faqat nom bilan ko'rinaveradi.

Revision ID: 5be53d0d8611
Revises: c9f2a4b71d06
Create Date: 2026-08-15 10:01:02.186524
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "5be53d0d8611"
down_revision: Union[str, Sequence[str], None] = "c9f2a4b71d06"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("categories", schema=None) as batch_op:
        batch_op.add_column(sa.Column("image", sa.String(length=255), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("categories", schema=None) as batch_op:
        batch_op.drop_column("image")
