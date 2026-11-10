"""add data integrity constraints

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-11-10

Moves rules that were only enforced by request validation into the
database, so no code path can store invalid data.

If existing rows violate a rule, PostgreSQL refuses to add the
constraint and this migration fails without changing anything.
Fix the offending rows and run it again.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


CHECKS: list[tuple[str, str, str]] = [
    (
        "products",
        "ck_products_stock_quantity_non_negative",
        "stock_quantity >= 0",
    ),
    (
        "products",
        "ck_products_minimum_stock_non_negative",
        "minimum_stock >= 0",
    ),
    (
        "products",
        "ck_products_prices_non_negative",
        "purchase_price >= 0 AND sale_price >= 0 AND average_cost >= 0",
    ),
    (
        "suppliers",
        "ck_suppliers_lead_time_days_range",
        "lead_time_days >= 0 AND lead_time_days <= 365",
    ),
    (
        "stock_movements",
        "ck_stock_movements_quantity_positive",
        "quantity > 0",
    ),
    (
        "stock_movements",
        "ck_stock_movements_levels_non_negative",
        "stock_before >= 0 AND stock_after >= 0",
    ),
    (
        "stock_movements",
        "ck_stock_movements_type_matches_levels",
        "(movement_type IN ('IN', 'ADJUSTMENT_IN', 'OPENING', 'RETURN')"
        " AND stock_after = stock_before + quantity)"
        " OR "
        "(movement_type IN ('OUT', 'ADJUSTMENT_OUT', 'SALE')"
        " AND stock_after = stock_before - quantity)",
    ),
    (
        "stock_movements",
        "ck_stock_movements_unit_cost_non_negative",
        "unit_cost IS NULL OR unit_cost >= 0",
    ),
    (
        "stock_movements",
        "ck_stock_movements_stock_in_has_unit_cost",
        "movement_type <> 'IN' OR unit_cost IS NOT NULL",
    ),
    (
        "sales",
        "ck_sales_totals_non_negative",
        "total_amount >= 0 AND total_cost >= 0",
    ),
    (
        "sales",
        "ck_sales_gross_profit_consistent",
        "ABS(gross_profit - (total_amount - total_cost)) < 0.005",
    ),
    (
        "sale_items",
        "ck_sale_items_quantity_positive",
        "quantity > 0",
    ),
    (
        "sale_items",
        "ck_sale_items_unit_prices_non_negative",
        "unit_sale_price >= 0 AND unit_purchase_price >= 0",
    ),
    (
        "sale_items",
        "ck_sale_items_subtotal_consistent",
        "ABS(subtotal - unit_sale_price * quantity) < 0.005",
    ),
    (
        "sale_items",
        "ck_sale_items_cost_consistent",
        "ABS(cost - unit_purchase_price * quantity) < 0.005",
    ),
    (
        "sale_items",
        "ck_sale_items_gross_profit_consistent",
        "ABS(gross_profit - (subtotal - cost)) < 0.005",
    ),
    (
        "sale_returns",
        "ck_sale_returns_quantity_positive",
        "quantity > 0",
    ),
    (
        "sale_returns",
        "ck_sale_returns_amounts_non_negative",
        "refund_amount >= 0 AND cost_amount >= 0",
    ),
]

# Sale totals are widened so a large sale cannot overflow them.
WIDENED: list[tuple[str, str]] = [
    ("sales", "total_amount"),
    ("sales", "total_cost"),
    ("sales", "gross_profit"),
    ("sale_items", "subtotal"),
    ("sale_items", "cost"),
    ("sale_items", "gross_profit"),
]

SERVER_DEFAULT_NOW = ["sales", "stock_movements", "sale_returns"]


def upgrade() -> None:
    for table, column in WIDENED:
        op.alter_column(
            table,
            column,
            type_=sa.Numeric(precision=14, scale=2),
            existing_type=sa.Numeric(precision=12, scale=2),
            existing_nullable=False,
        )

    for table, name, condition in CHECKS:
        op.create_check_constraint(name, table, condition)

    op.create_unique_constraint(
        "uq_sale_items_sale_product", "sale_items", ["sale_id", "product_id"]
    )

    for table in SERVER_DEFAULT_NOW:
        op.alter_column(
            table,
            "created_at",
            server_default=sa.func.now(),
            existing_type=sa.DateTime(timezone=True),
            existing_nullable=False,
        )

    op.drop_index(
        "ix_stock_movements_product_id", table_name="stock_movements"
    )
    op.create_index(
        "ix_stock_movements_product_created_at",
        "stock_movements",
        ["product_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_stock_movements_product_created_at",
        table_name="stock_movements",
    )
    op.create_index(
        "ix_stock_movements_product_id", "stock_movements", ["product_id"]
    )

    for table in SERVER_DEFAULT_NOW:
        op.alter_column(
            table,
            "created_at",
            server_default=None,
            existing_type=sa.DateTime(timezone=True),
            existing_nullable=False,
        )

    op.drop_constraint(
        "uq_sale_items_sale_product", "sale_items", type_="unique"
    )

    for table, name, _ in reversed(CHECKS):
        op.drop_constraint(name, table, type_="check")

    for table, column in WIDENED:
        op.alter_column(
            table,
            column,
            type_=sa.Numeric(precision=12, scale=2),
            existing_type=sa.Numeric(precision=14, scale=2),
            existing_nullable=False,
        )
