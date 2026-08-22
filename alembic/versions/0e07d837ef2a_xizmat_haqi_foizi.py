"""xizmat haqi foizi

Restoran hisobga qo'shadigan foiz ("15% xizmat uchun").

Ikki joyda saqlanadi va bu ataylab. `restaurants.service_percent` —
hozirgi sozlama. `orders.service_percent` — buyurtma paytidagi NUSXA:
egasi ertaga foizni ko'tarsa, kechagi buyurtmaning hisobi o'zgarib
ketmasligi kerak. Xuddi taom narxi nusxa bo'lib saqlangani kabi.

Ikkalasi ham `0` dan boshlanadi, ya'ni mavjud restoranlarda hech narsa
o'zgarmaydi: xizmat haqi faqat egasi o'zi yoqqanda paydo bo'ladi.


Revision ID: 0e07d837ef2a
Revises: f4c50697052c
Create Date: 2026-08-22 09:43:29.010230

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0e07d837ef2a'
down_revision: Union[str, Sequence[str], None] = 'f4c50697052c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # `server_default` SHART: ustun `NOT NULL` va mavjud qatorlarda
    # qiymat yo'q. Usiz migratsiya "Cannot add a NOT NULL column with
    # default value NULL" deb yiqiladi — mahalliy bazada ham, prodda ham.
    for jadval in ("orders", "restaurants"):
        with op.batch_alter_table(jadval, schema=None) as batch_op:
            batch_op.add_column(
                sa.Column("service_percent", sa.Integer(), nullable=False,
                          server_default="0")
            )


def downgrade() -> None:
    """Downgrade schema."""
    for jadval in ("restaurants", "orders"):
        with op.batch_alter_table(jadval, schema=None) as batch_op:
            batch_op.drop_column("service_percent")
