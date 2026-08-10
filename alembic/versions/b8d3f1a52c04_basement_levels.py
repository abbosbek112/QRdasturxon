"""basement levels

Revision ID: b8d3f1a52c04
Revises: a2c5e91b7d64
Create Date: 2026-08-10 12:10:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'b8d3f1a52c04'
down_revision: Union[str, Sequence[str], None] = 'a2c5e91b7d64'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Yerto'lani manfiy qavatga o'tkazadi.

    Ilgari `floor = 0` "yerto'la" degani edi va yerto'la bitta bo'lishi
    mumkin edi. Bir nechta daraja kerak bo'lgach bu chalkash bo'lib qoldi:
    `0` birinchi yerto'la, `-1` ikkinchisi bo'lardi, ya'ni raqam darajani
    aytmasdi.

    Endi `-1` = 1-yerto'la, `-2` = 2-yerto'la. Raqamning o'zi darajani
    bildiradi va `0` umuman ishlatilmaydi.
    """
    op.execute("UPDATE zones SET floor = -1 WHERE floor = 0")


def downgrade() -> None:
    """Faqat 1-yerto'la qaytariladi.

    Chuqurroq darajalar eski sxemada umuman ifodalanmaydi — ular ham
    yerto'la bo'lib birlashib qoladi. Bu ma'lumot yo'qotish, lekin
    downgrade allaqachon shunday: eski model bunday binoni bilmaydi.
    """
    op.execute("UPDATE zones SET floor = 0 WHERE floor < 0")
