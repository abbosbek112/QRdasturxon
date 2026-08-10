"""zone floor

Revision ID: f6b12d4a7c08
Revises: e4a90c2b81f3
Create Date: 2026-08-09 12:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f6b12d4a7c08'
down_revision: Union[str, Sequence[str], None] = 'e4a90c2b81f3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Bo'lim qaysi qavatda.

    Qavat bo'limda saqlanadi, stolda emas: bitta bo'lim ikki qavatga bo'linib
    ketmaydi. Shu bilan uchinchi daraja (qavat → bo'lim → stol) o'rniga
    ikkitasi qoladi va interfeys soddaligicha turadi.

    Mavjud bo'limlar birinchi qavatda deb hisoblanadi.
    """
    op.add_column(
        "zones",
        sa.Column("floor", sa.Integer(), nullable=False, server_default="1"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("zones", "floor")
