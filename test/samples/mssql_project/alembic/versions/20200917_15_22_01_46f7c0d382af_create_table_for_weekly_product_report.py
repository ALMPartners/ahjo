"""Create table for weekly product_report

Revision ID: 46f7c0d382af
Revises: 9d445cb42847
Create Date: 2020-09-17 15:22:01.751851

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '46f7c0d382af'
down_revision = '9d445cb42847'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('ProductWeekly',
    sa.Column('id', sa.Integer, primary_key=True),
    sa.Column('year', sa.Integer, nullable=False),
    sa.Column('week', sa.Integer, nullable=True),
    sa.Column('product_id', sa.Integer, nullable=True),
    sa.Column('sold_units', sa.Integer, nullable=True),
    sa.Column('sold_total_price', sa.Numeric(10,2), nullable=True),
    schema='report')


def downgrade():
    op.drop_table(table_name='ProductWeekly', schema='report')
