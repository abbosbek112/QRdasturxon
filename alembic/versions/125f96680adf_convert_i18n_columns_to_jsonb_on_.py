"""convert i18n columns to jsonb on postgres

Revision ID: 125f96680adf
Revises: 7f03be16655b
Create Date: 2026-07-31 11:18:00.418854

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '125f96680adf'
down_revision: Union[str, Sequence[str], None] = '7f03be16655b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Ko'p tilli matn saqlanadigan ustunlar
I18N_COLUMNS = (
    ("restaurants", ("description", "address")),
    ("categories", ("name",)),
    ("menu_items", ("name", "description", "ingredients")),
)


def _convert(target_type: str) -> None:
    """SQLite'da json va jsonb farqi yo'q — u yerda hech narsa qilinmaydi."""
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    for table, columns in I18N_COLUMNS:
        for column in columns:
            op.execute(
                f"ALTER TABLE {table} ALTER COLUMN {column} "
                f"TYPE {target_type} USING {column}::{target_type}"
            )


def upgrade() -> None:
    """Upgrade schema."""
    _convert("jsonb")


def downgrade() -> None:
    """Downgrade schema."""
    _convert("json")
