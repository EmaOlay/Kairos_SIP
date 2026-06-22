"""add publicada column to propuestas_generadas

Agrega columna publicada para permitir que las propuestas sean compartidas
entre usuarios. Por defecto todas son privadas (false).

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "propuestas_generadas",
        sa.Column("publicada", sa.Boolean(), nullable=False, server_default="false"),
    )


def downgrade() -> None:
    op.drop_column("propuestas_generadas", "publicada")
