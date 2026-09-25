"""Auth/session hardening: users.token_version for server-side session
revocation (see security/jwt.py and api/deps.py).

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-26

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users", sa.Column("token_version", sa.Integer, nullable=False, server_default="0")
    )


def downgrade() -> None:
    op.drop_column("users", "token_version")
