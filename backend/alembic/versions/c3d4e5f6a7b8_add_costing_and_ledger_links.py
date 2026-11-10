"""add costing and ledger links

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-11-10

Schema:
* products.average_cost          moving weighted average cost
* stock_movements.unit_cost      cost per unit for the movement
* stock_movements.sale_id        link from a SALE movement to its sale

Data backfills for rows created before this migration:
* average_cost starts at the product's purchase price, the only cost
  known for existing stock.
* unit_cost on existing movements is set to that same purchase price.
* sale_id is recovered from the "Sale <uuid>" note that sale
  movements were given.
* Products whose stock was entered at creation had no movement for
  it. An OPENING movement is inserted so that movements add up to
  the current stock level.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "products",
        sa.Column(
            "average_cost",
            sa.Numeric(precision=14, scale=4),
            nullable=True,
        ),
    )
    op.execute("UPDATE products SET average_cost = purchase_price")
    op.alter_column("products", "average_cost", nullable=False)

    op.add_column(
        "stock_movements",
        sa.Column(
            "unit_cost",
            sa.Numeric(precision=14, scale=4),
            nullable=True,
        ),
    )
    op.add_column(
        "stock_movements",
        sa.Column("sale_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_stock_movements_sale_id",
        "stock_movements",
        "sales",
        ["sale_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_stock_movements_sale_id", "stock_movements", ["sale_id"]
    )

    op.execute(
        """
        UPDATE stock_movements AS m
        SET unit_cost = p.purchase_price
        FROM products AS p
        WHERE p.id = m.product_id
        """
    )

    op.execute(
        """
        UPDATE stock_movements AS m
        SET sale_id = s.id
        FROM sales AS s
        WHERE m.movement_type = 'SALE'
          AND m.note = 'Sale ' || s.id::text
        """
    )

    # Opening quantity = the level before the first recorded
    # movement, or the current level if nothing was ever recorded.
    op.execute(
        """
        INSERT INTO stock_movements (
            id, business_id, product_id, movement_type, quantity,
            stock_before, stock_after, unit_cost, note, created_at
        )
        SELECT
            gen_random_uuid(),
            p.business_id,
            p.id,
            'OPENING',
            o.quantity,
            0,
            o.quantity,
            p.purchase_price,
            'Opening stock (backfilled by migration)',
            LEAST(
                p.created_at,
                o.first_movement_at - INTERVAL '1 millisecond'
            )
        FROM products AS p
        CROSS JOIN LATERAL (
            SELECT
                COALESCE(
                    (
                        SELECT m.stock_before
                        FROM stock_movements AS m
                        WHERE m.product_id = p.id
                        ORDER BY m.created_at, m.id
                        LIMIT 1
                    ),
                    p.stock_quantity
                ) AS quantity,
                (
                    SELECT MIN(m.created_at)
                    FROM stock_movements AS m
                    WHERE m.product_id = p.id
                ) AS first_movement_at
        ) AS o
        WHERE o.quantity > 0
        """
    )


def downgrade() -> None:
    op.execute(
        "DELETE FROM stock_movements WHERE movement_type = 'OPENING'"
    )
    op.drop_index(
        "ix_stock_movements_sale_id", table_name="stock_movements"
    )
    op.drop_constraint(
        "fk_stock_movements_sale_id",
        "stock_movements",
        type_="foreignkey",
    )
    op.drop_column("stock_movements", "sale_id")
    op.drop_column("stock_movements", "unit_cost")
    op.drop_column("products", "average_cost")
