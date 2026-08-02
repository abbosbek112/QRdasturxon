"""separate login and signup attempts

Revision ID: 92565c21fe2a
Revises: 081cd93759c6
Create Date: 2026-08-02 20:41:18.408981

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '92565c21fe2a'
down_revision: Union[str, Sequence[str], None] = '081cd93759c6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Urinish turini ajratish: login va signup alohida sanaladi.

    server_default kerak: jadvalda allaqachon yozuvlar bor. Ularning
    hammasi login urinishlari edi, shuning uchun standart qiymat 'login'.
    """
    op.add_column(
        "login_attempts",
        sa.Column("kind", sa.String(length=16), nullable=False, server_default="login"),
    )
    # Cheklov har so'rovda "shu IP, shu tur, shu oyna" deb sanaydi —
    # ikkovi birga indekslansa qidiruv jadval bo'ylab yugurmaydi
    op.create_index("ix_login_attempts_kind", "login_attempts", ["kind"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_login_attempts_kind", table_name="login_attempts")
    op.drop_column("login_attempts", "kind")
