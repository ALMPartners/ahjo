"""Create table store.ProductCategory

Revision ID: a8877159cdff
Revises: 46f7c0d382af
Create Date: 2021-04-16 12:00:11.679121

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a8877159cdff'
down_revision = '46f7c0d382af'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('ProductCategory',
    sa.Column('id', sa.Integer, primary_key=True),
    sa.Column('name', sa.String(255), nullable=False),
    sa.Column('description', sa.String(255), nullable=True),
    schema='store')


def downgrade():
    op.drop_table(table_name='ProductCategory', schema='store')
