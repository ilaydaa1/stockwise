"""Writes the demo account's data to CSV files.

One file per table, plus a ``ground_truth`` folder holding numbers
that exist only because the data is simulated, and a manifest
describing how the dataset was made.

Output is deterministic: rows are sorted, values are formatted the
same way on every database, and nothing time-of-export dependent is
written. The same seed therefore gives byte-identical files.
"""
import csv
import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from sqlalchemy.orm import Session

from stockwise.app.models.category import Category
from stockwise.app.models.product import Product
from stockwise.app.models.sale import Sale
from stockwise.app.models.sale_item import SaleItem
from stockwise.app.models.sale_return import SaleReturn
from stockwise.app.models.stock_movement import StockMovement
from stockwise.app.models.supplier import Supplier
from stockwise.datagen import config as cfg
from stockwise.datagen.simulation import SimulationResult


# Decimal places per column, so values look the same whether they
# were read from PostgreSQL or SQLite.
FOUR_PLACES = {"average_cost", "unit_cost"}

TABLES = {
    "categories": (
        Category,
        ["id", "name", "created_at"],
    ),
    "suppliers": (
        Supplier,
        ["id", "name", "lead_time_days", "created_at"],
    ),
    "products": (
        Product,
        [
            "id", "sku", "name", "category_id", "supplier_id",
            "purchase_price", "sale_price", "average_cost",
            "stock_quantity", "minimum_stock", "is_active", "created_at",
        ],
    ),
    "sales": (
        Sale,
        ["id", "total_amount", "total_cost", "gross_profit", "created_at"],
    ),
    "sale_items": (
        SaleItem,
        [
            "id", "sale_id", "product_id", "quantity", "unit_sale_price",
            "unit_purchase_price", "subtotal", "cost", "gross_profit",
        ],
    ),
    "sale_returns": (
        SaleReturn,
        [
            "id", "sale_item_id", "quantity", "refund_amount",
            "cost_amount", "reason", "created_at",
        ],
    ),
    "stock_movements": (
        StockMovement,
        [
            "id", "product_id", "movement_type", "quantity",
            "stock_before", "stock_after", "unit_cost", "sale_id",
            "sale_return_id", "note", "created_at",
        ],
    ),
}


def _format(column: str, value) -> str:
    if value is None:
        return ""

    if isinstance(value, bool):
        return "true" if value else "false"

    if isinstance(value, UUID):
        return str(value)

    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)

        return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    if isinstance(value, (Decimal, float)):
        places = 4 if column in FOUR_PLACES else 2

        return f"{Decimal(str(value)):.{places}f}"

    return str(value)


def _write(path: Path, header: list[str], rows) -> int:
    count = 0

    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(header)

        for row in rows:
            writer.writerow(row)
            count += 1

    return count


def _query(db: Session, name: str, business_id: UUID):
    model, _ = TABLES[name]

    if name == "sale_items":
        return (
            db.query(SaleItem)
            .join(Sale, Sale.id == SaleItem.sale_id)
            .filter(Sale.business_id == business_id)
            .order_by(Sale.created_at, SaleItem.id)
        )

    query = db.query(model).filter(model.business_id == business_id)

    if name in ("categories", "suppliers"):
        return query.order_by(model.name)

    if name == "products":
        return query.order_by(Product.sku)

    return query.order_by(model.created_at, model.id)


def build_manifest(
    result: SimulationResult,
    row_counts: dict[str, int],
) -> dict:
    config = result.config

    return {
        "synthetic": True,
        "notice": (
            "All data in this folder is artificial. It was produced by "
            "a simulation and does not describe any real business, "
            "person or transaction."
        ),
        "generator": "python -m stockwise.datagen generate",
        "seed": config.seed,
        "period": {
            "start": config.start.isoformat(),
            "end": config.end.isoformat(),
            "days": (config.end - config.start).days + 1,
        },
        "timezone": config.timezone,
        "timestamps": "UTC, ISO 8601",
        "currency": "TRY",
        "costing_method": "moving weighted average cost",
        "row_counts": row_counts,
        "simulation_totals": {
            "units_demanded": result.demand_units,
            "units_sold": result.sold_units,
            "units_lost_to_stockouts": result.lost_units,
            "fill_rate": round(result.fill_rate, 4),
        },
        "scenarios": {
            "supplier_delays": [
                {
                    "supplier": delay.supplier,
                    "orders_placed_from": delay.start.isoformat(),
                    "orders_placed_to": delay.end.isoformat(),
                    "extra_days": delay.extra_days,
                    "description": delay.label,
                }
                for delay in config.supplier_delays
            ],
            "bulk_purchases": [
                {
                    "sku": bulk.sku,
                    "date": bulk.on.isoformat(),
                    "quantity": bulk.quantity,
                    "discount_percent": bulk.discount_percent,
                    "description": bulk.label,
                }
                for bulk in config.bulk_purchases
            ],
            "demand_spikes": [
                {
                    "sku": spike.sku,
                    "start": spike.start.isoformat(),
                    "end": spike.end.isoformat(),
                    "multiplier": spike.multiplier,
                    "description": spike.label,
                }
                for spike in config.demand_spikes
            ],
            "supplier_cost_changes": [
                {
                    "supplier": change.supplier,
                    "date": change.on.isoformat(),
                    "percent": round(change.percent * 100, 2),
                    "sale_prices_follow_after_days": cfg.PRICE_FOLLOW_DAYS,
                }
                for change in config.cost_changes
            ],
            "product_launches": [
                {"sku": spec.sku, "date": spec.launch.isoformat()}
                for spec in config.products
                if spec.launch is not None and spec.launch > config.start
            ],
            "fading_products": [
                {"sku": spec.sku, "demand_fades_from": spec.fade_from.isoformat()}
                for spec in config.products
                if spec.fade_from is not None
            ],
            "products_that_barely_sell": [
                spec.sku for spec in config.products if spec.velocity == "D"
            ],
            "special_days": [
                {
                    "date": special.on.isoformat(),
                    "demand_factor": special.factor,
                    "description": special.label,
                    "categories": (
                        list(special.categories)
                        if special.categories
                        else "all"
                    ),
                }
                for special in config.special_days
            ],
        },
    }


def export_dataset(
    db: Session,
    business_id: UUID,
    result: SimulationResult,
    out_dir: Path,
) -> dict[str, int]:
    """Write every file and return the row count of each."""
    out_dir.mkdir(parents=True, exist_ok=True)
    truth_dir = out_dir / "ground_truth"
    truth_dir.mkdir(exist_ok=True)

    row_counts: dict[str, int] = {}

    for name, (_, columns) in TABLES.items():
        row_counts[name] = _write(
            out_dir / f"{name}.csv",
            columns,
            (
                [_format(column, getattr(row, column)) for column in columns]
                for row in _query(db, name, business_id).yield_per(5000)
            ),
        )

    row_counts["ground_truth/daily_demand"] = _write(
        truth_dir / "daily_demand.csv",
        [
            "date", "sku", "demand_units", "sold_units", "lost_units",
            "opening_stock", "closing_stock",
        ],
        (
            [
                row.day.isoformat(), row.sku, row.demand_units,
                row.sold_units, row.lost_units, row.opening_stock,
                row.closing_stock,
            ]
            for row in result.daily_truth
        ),
    )

    row_counts["ground_truth/purchasing_policy"] = _write(
        truth_dir / "purchasing_policy.csv",
        [
            "sku", "base_daily_demand", "yearly_trend", "minimum_stock",
            "order_quantity", "opening_stock",
        ],
        (
            [
                policy.sku,
                f"{policy.base_daily_demand:.4f}",
                f"{policy.yearly_trend:.4f}",
                policy.minimum_stock,
                policy.order_quantity,
                policy.opening_stock,
            ]
            for policy in sorted(
                result.policies.values(),
                key=lambda policy: policy.sku,
            )
        ),
    )

    manifest = build_manifest(result, row_counts)

    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    return row_counts
