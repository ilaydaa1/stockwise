"""add sale returns

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-11-10

A return row points at the sale item it reverses and stores the
refund and cost amounts computed from that item's frozen prices.
RETURN stock movements link back to it.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sale_returns",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("business_id", sa.Uuid(), nullable=False),
        sa.Column("sale_item_id", sa.Uuid(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column(
            "refund_amount",
            sa.Numeric(precision=14, scale=2),
            nullable=False,
        ),
        sa.Column(
            "cost_amount",
            sa.Numeric(precision=14, scale=2),
            nullable=False,
        ),
        sa.Column("reason", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["business_id"], ["businesses.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["sale_item_id"], ["sale_items.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_sale_returns_sale_item_id", "sale_returns", ["sale_item_id"]
    )
    op.create_index(
        "ix_sale_returns_business_created_at",
        "sale_returns",
        ["business_id", "created_at"],
    )

    op.add_column(
        "stock_movements",
        sa.Column("sale_return_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_stock_movements_sale_return_id",
        "stock_movements",
        "sale_returns",
        ["sale_return_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_stock_movements_sale_return_id",
        "stock_movements",
        ["sale_return_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_stock_movements_sale_return_id", table_name="stock_movements"
    )
    op.drop_constraint(
        "fk_stock_movements_sale_return_id",
        "stock_movements",
        type_="foreignkey",
    )
    op.drop_column("stock_movements", "sale_return_id")
    op.drop_index(
        "ix_sale_returns_business_created_at", table_name="sale_returns"
    )
    op.drop_index("ix_sale_returns_sale_item_id", table_name="sale_returns")
    op.drop_table("sale_returns")
