"""defer the sale item to product check until commit

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-11-11

Deleting a business removes its products and, through its sales, the
sale lines that point at those products. PostgreSQL checked the
product reference immediately, found sale lines that had not been
removed yet, and refused the whole delete.

The reference is now checked when the transaction commits. By then a
business delete has removed both sides. Deleting a single product
that still has sale lines is refused exactly as before.
"""
from typing import Sequence, Union

from alembic import op


revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint(
        "sale_items_product_id_fkey", "sale_items", type_="foreignkey"
    )
    op.create_foreign_key(
        "sale_items_product_id_fkey",
        "sale_items",
        "products",
        ["product_id"],
        ["id"],
        deferrable=True,
        initially="DEFERRED",
    )


def downgrade() -> None:
    op.drop_constraint(
        "sale_items_product_id_fkey", "sale_items", type_="foreignkey"
    )
    op.create_foreign_key(
        "sale_items_product_id_fkey",
        "sale_items",
        "products",
        ["product_id"],
        ["id"],
    )
