"""kombo qoshimchalari

Kombo tarkibiga menyuda turmagan narsalarni ham qo'shish uchun:
"cheksiz choy", "shirinlik sovg'a", "ikki kishilik idish".

Shuning uchun `item_id` endi bo'sh bo'lishi mumkin va yonida
`custom_name` turadi. Har qatorda aynan bittasi to'ldiriladi.

Orqaga qaytarish MA'LUMOT YO'QOTADI: qo'shimcha qatorlarda `item_id`
bo'sh va ustunni majburiy qilib bo'lmaydi. Shuning uchun ular avval
o'chiriladi — bu ataylab va ochiq qilingan, jimgina yiqilishdan
ko'ra tushunarli.

Revision ID: f4c50697052c
Revises: 2f0106883b46
Create Date: 2026-08-16 10:47:32.588114
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f4c50697052c"
down_revision: Union[str, Sequence[str], None] = "2f0106883b46"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("combo_lines", schema=None) as batch_op:
        batch_op.add_column(sa.Column("custom_name", sa.String(length=120), nullable=True))
        batch_op.alter_column("item_id", existing_type=sa.INTEGER(), nullable=True)


def downgrade() -> None:
    # Taomga bog'lanmagan qatorlar ustunni majburiy qilishga to'sqinlik
    # qiladi — ular avval olib tashlanadi
    op.execute("DELETE FROM combo_lines WHERE item_id IS NULL")
    with op.batch_alter_table("combo_lines", schema=None) as batch_op:
        batch_op.alter_column("item_id", existing_type=sa.INTEGER(), nullable=False)
        batch_op.drop_column("custom_name")
