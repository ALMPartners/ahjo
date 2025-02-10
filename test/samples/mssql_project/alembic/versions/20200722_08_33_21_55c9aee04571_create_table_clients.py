"""Create table clients

Revision ID: 55c9aee04571
Revises: 00684a7208eb
Create Date: 2020-07-22 08:33:21.026889

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "55c9aee04571"
down_revision = "00684a7208eb"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "Clients",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(255), nullable=True),
        sa.Column("address", sa.String(255), nullable=True),
        sa.Column("zip_code", sa.String(255), nullable=True),
        sa.Column("country", sa.String(255), nullable=True),
        sa.Column("date_of_birth", sa.Date, nullable=True),
        schema="store",
    )


def downgrade():
    op.drop_table(table_name="Clients", schema="store")
