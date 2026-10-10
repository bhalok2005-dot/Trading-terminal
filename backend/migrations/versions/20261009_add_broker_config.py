"""Add broker config to accounts

Revision ID: 20261009_add_broker_config
Revises: 20261009_initial_schema
Create Date: 2026-10-09 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20261009_add_broker_config"
down_revision: Union[str, None] = "20261009_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("accounts", sa.Column("broker_config", sa.String(length=5000), nullable=True))


def downgrade() -> None:
    op.drop_column("accounts", "broker_config")
