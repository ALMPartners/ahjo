"""Create table products

Revision ID: 7ed350929292
Revises: 55c9aee04571
Create Date: 2020-07-22 08:47:25.746591

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "7ed350929292"
down_revision = "55c9aee04571"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "Products",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("category_id", sa.Integer, nullable=False),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column("unit_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("units_in_package", sa.Integer, nullable=True),
        sa.Column("package_weight", sa.Numeric(13, 3), nullable=True),
        sa.Column("manufacturer", sa.String(255), nullable=True),
        schema="store",
    )


def downgrade():
    op.drop_table(table_name="Products", schema="store")
