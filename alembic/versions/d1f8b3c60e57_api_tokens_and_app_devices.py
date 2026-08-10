"""api tokens and app devices

Revision ID: d1f8b3c60e57
Revises: c7e2f019a4b8
Create Date: 2026-08-08 09:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd1f8b3c60e57'
down_revision: Union[str, Sequence[str], None] = 'c7e2f019a4b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Afitsant ilovasi uchun: kirish kaliti va qurilma tokeni.

    Ikkalasi ham xodimga CASCADE bilan bog'langan — hisob o'chirilsa kalit
    ham, bildirishnoma qurilmasi ham qolmaydi.
    """
    op.create_table(
        "api_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("label", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index(op.f("ix_api_tokens_user_id"), "api_tokens", ["user_id"])
    op.create_index(op.f("ix_api_tokens_token_hash"), "api_tokens", ["token_hash"], unique=True)

    op.create_table(
        "app_devices",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("expo_token", sa.String(length=255), nullable=False),
        sa.Column("platform", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("expo_token"),
    )
    op.create_index(op.f("ix_app_devices_user_id"), "app_devices", ["user_id"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_app_devices_user_id"), table_name="app_devices")
    op.drop_table("app_devices")

    op.drop_index(op.f("ix_api_tokens_token_hash"), table_name="api_tokens")
    op.drop_index(op.f("ix_api_tokens_user_id"), table_name="api_tokens")
    op.drop_table("api_tokens")
