"""Command line for the synthetic dataset.

    python -m stockwise.datagen generate --reset
    python -m stockwise.datagen validate
    python -m stockwise.datagen export

Run from the ``backend`` folder. ``generate`` simulates the history,
loads it into the demo account, checks its integrity and, only if the
checks pass, writes the CSV files.
"""
import argparse
import sys
import time
from datetime import date
from pathlib import Path

from sqlalchemy import create_engine, func
from sqlalchemy.orm import Session, sessionmaker

from stockwise.app.models.sale import Sale
from stockwise.app.models.sale_item import SaleItem
from stockwise.app.models.sale_return import SaleReturn
from stockwise.app.models.stock_movement import StockMovement
from stockwise.app.services.integrity import check_integrity
from stockwise.datagen import config as cfg
from stockwise.datagen.export import export_dataset
from stockwise.datagen.loader import (
    DEMO_PASSWORD_ENV,
    DemoDataExistsError,
    find_demo_business,
    load,
)
from stockwise.datagen.simulation import simulate


DEFAULT_OUT_DIR = Path(__file__).resolve().parents[3] / "data" / "synthetic"


def _session(args) -> Session:
    if args.database_url:
        engine = create_engine(args.database_url)
    else:
        from stockwise.app.db.base import engine

    if args.create_schema:
        import stockwise.app.models  # noqa: F401  (registers tables)
        from stockwise.app.db.base import Base

        Base.metadata.create_all(bind=engine)

    return sessionmaker(bind=engine, autoflush=False, autocommit=False)()


def _config(args) -> cfg.SimulationConfig:
    return cfg.default_config(
        seed=args.seed,
        start=args.start,
        end=args.end,
    )


def _report_issues(issues) -> None:
    print(f"Integrity check FAILED: {len(issues)} kind(s) of problem")

    for issue in issues:
        print(f"  - {issue.check}: {issue.count} row(s). {issue.description}")
        print(f"    examples: {', '.join(issue.examples)}")


def _print_statistics(db: Session, business_id, result) -> None:
    sales, revenue, cost = db.query(
        func.count(Sale.id),
        func.coalesce(func.sum(Sale.total_amount), 0),
        func.coalesce(func.sum(Sale.total_cost), 0),
    ).filter(Sale.business_id == business_id).one()

    lines = (
        db.query(func.count(SaleItem.id))
        .join(Sale, Sale.id == SaleItem.sale_id)
        .filter(Sale.business_id == business_id)
        .scalar()
    )

    returns, refunds = db.query(
        func.count(SaleReturn.id),
        func.coalesce(func.sum(SaleReturn.refund_amount), 0),
    ).filter(SaleReturn.business_id == business_id).one()

    movements = dict(
        db.query(StockMovement.movement_type, func.count(StockMovement.id))
        .filter(StockMovement.business_id == business_id)
        .group_by(StockMovement.movement_type)
        .all()
    )

    stockout_days = sum(
        1 for row in result.daily_truth if row.opening_stock == 0
    )

    print(f"  sales                {sales:>12,}")
    print(f"  sale lines           {lines:>12,}")
    print(f"  returns              {returns:>12,}")
    print(f"  gross revenue (TRY)  {float(revenue):>12,.2f}")
    print(f"  refunds (TRY)        {float(refunds):>12,.2f}")
    print(f"  cost of goods (TRY)  {float(cost):>12,.2f}")

    for movement_type in sorted(movements):
        label = f"movements {movement_type}"
        print(f"  {label:<21}{movements[movement_type]:>12,}")

    print(f"  units demanded       {result.demand_units:>12,}")
    print(f"  units sold           {result.sold_units:>12,}")
    print(f"  units lost (no stock){result.lost_units:>12,}")
    print(f"  fill rate            {result.fill_rate:>12.1%}")
    print(f"  product-days at zero {stockout_days:>12,}")


def generate(args) -> int:
    config = _config(args)

    print(
        f"Simulating {config.start} to {config.end} "
        f"with seed {config.seed} ..."
    )
    result = simulate(config)
    print(f"  {len(result.events):,} events")

    db = _session(args)

    try:
        print("Loading into the demo account ...")
        started = time.monotonic()

        try:
            loaded = load(db, result, reset=args.reset)
        except DemoDataExistsError:
            print(
                "The demo account already has data. "
                "Run again with --reset to replace it."
            )
            return 1

        print(f"  done in {time.monotonic() - started:.0f}s")

        print("Checking integrity ...")
        issues = check_integrity(db, loaded.business_id)

        if issues:
            _report_issues(issues)
            print("Nothing was exported.")
            return 1

        print("  all checks passed")

        if not args.no_export:
            counts = export_dataset(db, loaded.business_id, result, args.out)
            print(f"Exported to {args.out}")

            for name, count in counts.items():
                print(f"  {name:<32}{count:>10,} rows")

        print("Dataset statistics")
        _print_statistics(db, loaded.business_id, result)

        if loaded.demo_login_enabled:
            print(f"Demo login: {cfg.DEMO_USER_EMAIL}")
        else:
            print(
                f"Demo login is disabled. Set {DEMO_PASSWORD_ENV} and "
                "regenerate to be able to sign in as "
                f"{cfg.DEMO_USER_EMAIL}."
            )

        return 0
    finally:
        db.close()


def validate(args) -> int:
    db = _session(args)

    try:
        business = find_demo_business(db)

        if business is None:
            print("No demo data found. Run generate first.")
            return 1

        issues = check_integrity(db, business.id)

        if issues:
            _report_issues(issues)
            return 1

        print("All integrity checks passed.")
        return 0
    finally:
        db.close()


def export(args) -> int:
    db = _session(args)

    try:
        business = find_demo_business(db)

        if business is None:
            print("No demo data found. Run generate first.")
            return 1

        issues = check_integrity(db, business.id)

        if issues:
            _report_issues(issues)
            print("Nothing was exported.")
            return 1

        # The ground-truth files come from the simulation, which is
        # cheap to repeat and identical for the same seed.
        result = simulate(_config(args))
        counts = export_dataset(db, business.id, result, args.out)

        print(f"Exported to {args.out}")

        for name, count in counts.items():
            print(f"  {name:<32}{count:>10,} rows")

        return 0
    finally:
        db.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m stockwise.datagen",
        description="Synthetic historical data for StockWise.",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    for name, handler in (
        ("generate", generate),
        ("validate", validate),
        ("export", export),
    ):
        command = commands.add_parser(name)
        command.set_defaults(handler=handler)
        command.add_argument(
            "--database-url",
            help="SQLAlchemy URL. Defaults to the application database.",
        )
        command.add_argument(
            "--create-schema",
            action="store_true",
            help="Create missing tables first (for a throwaway database; "
            "use Alembic for the real one).",
        )

        if name != "validate":
            command.add_argument("--seed", type=int, default=cfg.DEFAULT_SEED)
            command.add_argument(
                "--start",
                type=date.fromisoformat,
                default=cfg.DEFAULT_START,
            )
            command.add_argument(
                "--end",
                type=date.fromisoformat,
                default=cfg.DEFAULT_END,
            )
            command.add_argument(
                "--out",
                type=Path,
                default=DEFAULT_OUT_DIR,
                help="Folder for the CSV files.",
            )

        if name == "generate":
            command.add_argument(
                "--reset",
                action="store_true",
                help="Replace existing demo data.",
            )
            command.add_argument(
                "--no-export",
                action="store_true",
                help="Load and validate only.",
            )

    args = parser.parse_args(argv)

    return args.handler(args)


if __name__ == "__main__":
    sys.exit(main())
