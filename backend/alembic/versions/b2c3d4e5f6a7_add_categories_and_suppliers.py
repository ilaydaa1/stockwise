"""add categories and suppliers

Revision ID: b2c3d4e5f6a7
Revises: 73d0cdd8ed41
Create Date: 2026-11-10

Adds the two lookup tables and links products to them. The links are
composite foreign keys on (business_id, <ref>_id), so the database
itself rejects a product that points at another business's category
or supplier.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "73d0cdd8ed41"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "categories",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("business_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["business_id"], ["businesses.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "business_id", "name", name="uq_categories_business_name"
        ),
        sa.UniqueConstraint(
            "business_id", "id", name="uq_categories_business_id_id"
        ),
    )

    op.create_table(
        "suppliers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("business_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("lead_time_days", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["business_id"], ["businesses.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "business_id", "name", name="uq_suppliers_business_name"
        ),
        sa.UniqueConstraint(
            "business_id", "id", name="uq_suppliers_business_id_id"
        ),
    )

    op.add_column(
        "products", sa.Column("category_id", sa.Uuid(), nullable=True)
    )
    op.add_column(
        "products", sa.Column("supplier_id", sa.Uuid(), nullable=True)
    )

    op.create_foreign_key(
        "fk_products_category_same_business",
        "products",
        "categories",
        ["business_id", "category_id"],
        ["business_id", "id"],
    )
    op.create_foreign_key(
        "fk_products_supplier_same_business",
        "products",
        "suppliers",
        ["business_id", "supplier_id"],
        ["business_id", "id"],
    )

    op.create_index("ix_products_category_id", "products", ["category_id"])
    op.create_index("ix_products_supplier_id", "products", ["supplier_id"])


def downgrade() -> None:
    op.drop_index("ix_products_supplier_id", table_name="products")
    op.drop_index("ix_products_category_id", table_name="products")
    op.drop_constraint(
        "fk_products_supplier_same_business", "products", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_products_category_same_business", "products", type_="foreignkey"
    )
    op.drop_column("products", "supplier_id")
    op.drop_column("products", "category_id")
    op.drop_table("suppliers")
    op.drop_table("categories")
