"""push subscriptions

Revision ID: c7e2f019a4b8
Revises: b3a41c7d5e92
Create Date: 2026-08-07 16:55:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c7e2f019a4b8'
down_revision: Union[str, Sequence[str], None] = 'b3a41c7d5e92'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Afitsant qurilmalarining bildirishnoma obunasi.

    `endpoint` yagona: bir qurilma ikki marta obuna bo'lsa yozuv yangilanadi,
    ko'paymaydi. Xodim o'chirilsa obunalari ham ketadi (CASCADE).
    """
    op.create_table(
        "push_subscriptions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("endpoint", sa.String(length=512), nullable=False),
        sa.Column("p256dh", sa.String(length=255), nullable=False),
        sa.Column("auth", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("endpoint"),
    )
    op.create_index(
        op.f("ix_push_subscriptions_user_id"), "push_subscriptions", ["user_id"]
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_push_subscriptions_user_id"), table_name="push_subscriptions")
    op.drop_table("push_subscriptions")
