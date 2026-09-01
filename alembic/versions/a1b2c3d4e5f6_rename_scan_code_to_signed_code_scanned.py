"""rename scan code column to signed_code_scanned

Revision ID: a1b2c3d4e5f6
Revises: 2658412cd2d8
Create Date: 2026-08-26 15:30:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "2658412cd2d8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        op.execute("DROP TABLE IF EXISTS _alembic_tmp_scans")
        op.execute("ALTER TABLE scans RENAME COLUMN code TO signed_code_scanned")
    else:
        op.alter_column("scans", "code", new_column_name="signed_code_scanned")

    op.drop_index("ix_scans_code", table_name="scans")
    op.create_index(
        "ix_scans_signed_code_scanned",
        "scans",
        ["signed_code_scanned"],
        unique=False,
    )


def downgrade() -> None:
    bind = op.get_bind()
    op.drop_index("ix_scans_signed_code_scanned", table_name="scans")
    op.create_index("ix_scans_code", "scans", ["signed_code_scanned"], unique=False)

    if bind.dialect.name == "sqlite":
        op.execute("ALTER TABLE scans RENAME COLUMN signed_code_scanned TO code")
    else:
        op.alter_column("scans", "signed_code_scanned", new_column_name="code")
