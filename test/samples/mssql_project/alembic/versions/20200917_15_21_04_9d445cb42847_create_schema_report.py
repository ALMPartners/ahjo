"""Create schema report

Revision ID: 9d445cb42847
Revises: 7ed350929292
Create Date: 2020-09-17 15:21:04.532792

"""

from alembic import op
from sqlalchemy.sql import text
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "9d445cb42847"
down_revision = "7ed350929292"
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    connection.execute(sa.schema.CreateSchema("report"))


def downgrade():
    connection = op.get_bind()
    connection.execute(text("DROP SCHEMA report"))
