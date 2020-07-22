"""Create schema store

Revision ID: 00684a7208eb
Revises: 
Create Date: 2020-07-22 08:33:18.368134

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '00684a7208eb'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    connection.execute(sa.schema.CreateSchema('store'))


def downgrade():
    connection = op.get_bind()
    connection.execute("DROP SCHEMA store")
