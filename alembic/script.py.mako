## ============================================================================
## Template Mako para migraciones de Alembic.
##
## Que es esto?
##   Cada vez que corres `alembic revision` (con o sin --autogenerate),
##   Alembic genera un archivo nuevo en alembic/versions/ usando este template
##   como molde. Las variables ${...} se reemplazan en tiempo de generacion
##   (NO en runtime de la migracion):
##     - ${message}        -> el -m "..." que pasaste por CLI
##     - ${up_revision}    -> hash unico de esta revision (ej: "a1b2c3d4")
##     - ${down_revision}  -> hash de la revision anterior (None si es la 1ra)
##     - ${create_date}    -> timestamp de cuando se genero el archivo
##     - ${imports}        -> imports extra que el autogenerate detecto
##     - ${upgrades}       -> ops generadas por autogenerate (ej. op.create_table)
##     - ${downgrades}     -> ops inversas para hacer rollback
##
## Las lineas que empiezan con `## ` (como esta) son comentarios de Mako:
## NO aparecen en el archivo de migracion final, solo viven en el template.
##
## Una vez generada la migracion, tu funcion upgrade() corre con
## `alembic upgrade head` y downgrade() con `alembic downgrade -1`.
## ============================================================================
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

# revision identifiers, used by Alembic.
revision: str = ${repr(up_revision)}
down_revision: Union[str, None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
