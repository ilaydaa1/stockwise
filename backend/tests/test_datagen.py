"""Synthetic data generator: simulation, loading and export."""
import csv
import json
import random
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

import pytest

from stockwise.app.models.business import Business
from stockwise.app.models.product import Product
from stockwise.app.models.sale import Sale
from stockwise.app.models.sale_return import SaleReturn
from stockwise.app.models.stock_movement import StockMovement
from stockwise.app.models.user import User
from stockwise.app.services.integrity import check_integrity
from stockwise.datagen import config as cfg
from stockwise.datagen.config import default_config
from stockwise.datagen.export import export_dataset
from stockwise.datagen.loader import (
    DEMO_PASSWORD_ENV,
    DemoDataExistsError,
    delete_demo_data,
    find_demo_business,
    load,
)
from stockwise.datagen.simulation import (
    PriceChanged,
    ProductCreated,
    ReturnMade,
    SaleMade,
    StockAdjusted,
    StockReceived,
    month_factor,
    poisson,
    shelf_price,
    simulate,
)
from tests.test_sales import _create_product, _create_user_and_business


SHORT_END = cfg.DEFAULT_START + timedelta(days=44)


@pytest.fixture(scope="module")
def full():
    """The complete default history. Pure Python, under a second."""
    return simulate(default_config())


@pytest.fixture(scope="module")
def short():
    return simulate(default_config(end=SHORT_END))


class TestHelpers:
    def test_month_factor_equals_monthly_value_mid_month(self):
        category = cfg.CATEGORIES[0]

        assert month_factor(category, date(2026, 7, 16)) == pytest.approx(
            category.month_factors[6], abs=0.01
        )

    def test_month_factor_has_no_jump_at_month_boundaries(self):
        for category in cfg.CATEGORIES:
            day = date(2025, 8, 1)

            while day < date(2026, 8, 1):
                today = month_factor(category, day)
                tomorrow = month_factor(category, day + timedelta(days=1))

                assert abs(tomorrow - today) < 0.15, (category.key, day)

                day += timedelta(days=1)

    @pytest.mark.parametrize("rate", [0.3, 4.0, 45.0])
    def test_poisson_mean_matches_rate(self, rate):
        rng = random.Random(1)
        draws = [poisson(rng, rate) for _ in range(20_000)]

        assert sum(draws) / len(draws) == pytest.approx(rate, rel=0.05)
        assert min(draws) >= 0

    def test_poisson_of_zero_rate_is_zero(self):
        assert poisson(random.Random(1), 0) == 0

    @pytest.mark.parametrize(
        "value, expected",
        [("10.24", "10.00"), ("10.25", "10.50"), ("10.76", "11.00")],
    )
    def test_shelf_price_rounds_to_half_lira(self, value, expected):
        assert shelf_price(Decimal(value)) == Decimal(expected)


class TestSimulationIsReproducible:
    def test_same_seed_gives_identical_history(self, short):
        again = simulate(default_config(end=SHORT_END))

        assert again.events == short.events
        assert again.daily_truth == short.daily_truth
        assert again.policies == short.policies

    def test_different_seed_gives_different_history(self, short):
        other = simulate(default_config(seed=7, end=SHORT_END))

        assert other.events != short.events

    def test_product_parameters_do_not_depend_on_period_length(
        self, short, full
    ):
        assert short.policies == full.policies


class TestSimulationIsConsistent:
    def test_sales_never_exceed_stock_on_hand(self, full):
        for row in full.daily_truth:
            assert 0 <= row.sold_units <= row.opening_stock
            assert row.sold_units <= row.demand_units
            assert row.lost_units == row.demand_units - row.sold_units
            assert row.closing_stock >= 0

    def test_lost_demand_only_happens_when_stock_runs_out(self, full):
        for row in full.daily_truth:
            if row.lost_units:
                assert row.sold_units == row.opening_stock

    def test_event_timestamps_are_unique_and_ordered(self, full):
        timestamps = [event.at for event in full.events]

        assert timestamps == sorted(timestamps)
        assert len(set(timestamps)) == len(timestamps)

    def test_replaying_events_never_drives_stock_negative(self, full):
        """Independent check of what the loader will be asked to do."""
        stock: dict[str, int] = {}
        sold_lines: dict[tuple[int, str], int] = {}

        for event in full.events:
            if isinstance(event, ProductCreated):
                assert event.sku not in stock
                stock[event.sku] = event.opening_stock
            elif isinstance(event, StockReceived):
                stock[event.sku] += event.quantity
            elif isinstance(event, SaleMade):
                assert len({sku for sku, _ in event.lines}) == len(
                    event.lines
                )

                for sku, quantity in event.lines:
                    stock[sku] -= quantity
                    sold_lines[(event.ref, sku)] = quantity

                    assert stock[sku] >= 0, (event.at, sku)
            elif isinstance(event, ReturnMade):
                assert (
                    event.quantity
                    <= sold_lines[(event.sale_ref, event.sku)]
                )
                stock[event.sku] += event.quantity
            elif isinstance(event, StockAdjusted):
                sign = 1 if event.movement_type == "ADJUSTMENT_IN" else -1
                stock[event.sku] += sign * event.quantity

                assert stock[event.sku] >= 0

        closing = {}

        for row in full.daily_truth:
            closing[row.sku] = row.closing_stock

        assert stock == closing

    def test_sales_happen_during_opening_hours_local_time(self, full):
        from zoneinfo import ZoneInfo

        tz = ZoneInfo(cfg.TIMEZONE)

        for event in full.events:
            if isinstance(event, SaleMade):
                hour = event.at.astimezone(tz).hour

                assert cfg.OPENING_HOUR <= hour <= cfg.OPENING_HOUR + 12


class TestScenariosArePresent:
    def test_volume_is_in_the_intended_range(self, full):
        sales = [e for e in full.events if isinstance(e, SaleMade)]

        assert 20_000 <= len(sales) <= 30_000
        assert len(full.config.products) == 80
        assert 0.90 <= full.fill_rate <= 0.99

    def test_stockouts_exist_and_are_worst_for_seasonal_goods(self, full):
        category_of = {p.sku: p.category for p in full.config.products}
        demand = defaultdict(int)
        lost = defaultdict(int)

        for row in full.daily_truth:
            demand[category_of[row.sku]] += row.demand_units
            lost[category_of[row.sku]] += row.lost_units

        loss_rate = {key: lost[key] / demand[key] for key in demand}

        assert full.lost_units > 0
        assert loss_rate["winter"] == max(loss_rate.values())
        assert loss_rate["winter"] > 3 * loss_rate["beverages"]

    def test_seasonality_is_visible(self, full):
        category_of = {p.sku: p.category for p in full.config.products}
        monthly = defaultdict(int)

        for row in full.daily_truth:
            monthly[(category_of[row.sku], row.day.month, row.day.year)] += (
                row.demand_units
            )

        assert monthly[("beverages", 7, 2026)] > 1.6 * monthly[
            ("beverages", 1, 2026)
        ]
        assert monthly[("stationery", 9, 2025)] > 2.5 * monthly[
            ("stationery", 6, 2026)
        ]
        assert monthly[("winter", 12, 2025)] > 8 * monthly[
            ("winter", 6, 2026)
        ]

    def test_weekend_effect_is_visible(self, full):
        category_of = {p.sku: p.category for p in full.config.products}
        by_weekday = defaultdict(lambda: defaultdict(int))

        for row in full.daily_truth:
            by_weekday[category_of[row.sku]][row.day.weekday()] += (
                row.demand_units
            )

        assert by_weekday["toys"][5] > 1.4 * by_weekday["toys"][0]
        assert by_weekday["stationery"][6] < 0.7 * by_weekday["stationery"][0]

    def test_bulk_purchase_leaves_dead_stock(self, full):
        bulk = full.config.bulk_purchases[0]
        rows = [row for row in full.daily_truth if row.sku == bulk.sku]
        last_90_days = rows[-90:]

        assert rows[-1].closing_stock > 150
        assert sum(row.sold_units for row in last_90_days) == 0

    def test_products_that_barely_sell_end_with_stock(self, full):
        closing = {row.sku: row.closing_stock for row in full.daily_truth}
        sold = defaultdict(int)

        for row in full.daily_truth:
            sold[row.sku] += row.sold_units

        for spec in full.config.products:
            if spec.velocity == "D":
                assert closing[spec.sku] > 0
                assert sold[spec.sku] < 60

    def test_demand_spike_is_visible(self, full):
        spike = full.config.demand_spikes[0]
        length = (spike.end - spike.start).days + 1

        during = sum(
            row.demand_units
            for row in full.daily_truth
            if row.sku == spike.sku and spike.start <= row.day <= spike.end
        )
        before = sum(
            row.demand_units
            for row in full.daily_truth
            if row.sku == spike.sku
            and spike.start - timedelta(days=length) <= row.day < spike.start
        )

        assert during > 3 * max(before, 1)

    def test_supplier_delay_causes_stockouts(self, full):
        delay = full.config.supplier_delays[0]
        affected = {
            p.sku for p in full.config.products if p.supplier == delay.supplier
        }

        def lost_between(first, last):
            return sum(
                row.lost_units
                for row in full.daily_truth
                if row.sku in affected and first <= row.day <= last
            )

        window = timedelta(days=45)

        during = lost_between(delay.start, delay.start + window)
        year_later_free = lost_between(
            delay.start + timedelta(days=120),
            delay.start + timedelta(days=120) + window,
        )

        assert during > 3 * max(year_later_free, 1)

    def test_costs_and_prices_change_over_time(self, full):
        price_changes = [e for e in full.events if isinstance(e, PriceChanged)]
        costs_by_sku = defaultdict(set)

        for event in full.events:
            if isinstance(event, StockReceived):
                costs_by_sku[event.sku].add(event.unit_cost)

        assert len(price_changes) > 50
        assert sum(1 for costs in costs_by_sku.values() if len(costs) > 1) > 30

    def test_products_launch_mid_period(self, full):
        created = {
            e.sku: e.at.date()
            for e in full.events
            if isinstance(e, ProductCreated)
        }
        late = [sku for sku, day in created.items() if day > cfg.DEFAULT_START]

        assert len(created) == 80
        assert len(late) == 5

    def test_returns_and_adjustments_exist(self, full):
        returns = [e for e in full.events if isinstance(e, ReturnMade)]
        adjustments = [e for e in full.events if isinstance(e, StockAdjusted)]
        lines = sum(
            len(e.lines) for e in full.events if isinstance(e, SaleMade)
        )

        assert 0.005 < len(returns) / lines < 0.03
        assert {a.movement_type for a in adjustments} == {
            "ADJUSTMENT_IN",
            "ADJUSTMENT_OUT",
        }


class TestLoader:
    def test_loaded_history_passes_every_integrity_check(
        self, short, db_session
    ):
        loaded = load(db_session, short)

        assert check_integrity(db_session, loaded.business_id) == []

    def test_database_matches_the_simulation(self, short, db_session):
        loaded = load(db_session, short)

        expected_sales = sum(isinstance(e, SaleMade) for e in short.events)
        expected_returns = sum(isinstance(e, ReturnMade) for e in short.events)
        closing = {row.sku: row.closing_stock for row in short.daily_truth}

        assert db_session.query(Sale).count() == expected_sales
        assert db_session.query(SaleReturn).count() == expected_returns
        assert {
            product.sku: product.stock_quantity
            for product in db_session.query(Product).all()
        } == closing
        assert loaded.events_loaded == len(short.events)

    def test_products_carry_category_supplier_and_policy(
        self, short, db_session
    ):
        load(db_session, short)

        for product in db_session.query(Product).all():
            assert product.category_id is not None
            assert product.supplier_id is not None
            assert product.minimum_stock == (
                short.policies[product.sku].minimum_stock
            )

    def test_timestamps_are_historical(self, short, db_session):
        load(db_session, short)

        newest = (
            db_session.query(StockMovement.created_at)
            .order_by(StockMovement.created_at.desc())
            .first()[0]
        )

        assert newest.date() <= SHORT_END

    def test_refuses_to_overwrite_without_reset(self, short, db_session):
        load(db_session, short)

        with pytest.raises(DemoDataExistsError):
            load(db_session, short)

    def test_reset_reproduces_identical_rows(self, short, db_session):
        load(db_session, short)
        first = [
            (sale.id, sale.total_amount, sale.created_at)
            for sale in db_session.query(Sale).order_by(Sale.id).all()
        ]

        load(db_session, short, reset=True)
        db_session.expire_all()
        second = [
            (sale.id, sale.total_amount, sale.created_at)
            for sale in db_session.query(Sale).order_by(Sale.id).all()
        ]

        assert first == second
        assert len(first) > 1000

    def test_delete_removes_only_the_demo_account(self, short, db_session):
        _, other_business = _create_user_and_business(db_session)
        other_product = _create_product(db_session, other_business)
        other_product_id = other_product.id

        load(db_session, short)

        assert delete_demo_data(db_session) is True
        assert find_demo_business(db_session) is None
        assert db_session.query(Business).count() == 1
        assert db_session.query(Sale).count() == 0
        assert db_session.query(StockMovement).count() == 0
        assert db_session.get(Product, other_product_id) is not None
        assert delete_demo_data(db_session) is False

    def test_demo_login_is_disabled_without_a_password(
        self, short, db_session, client, monkeypatch
    ):
        monkeypatch.delenv(DEMO_PASSWORD_ENV, raising=False)

        loaded = load(db_session, short)

        assert loaded.demo_login_enabled is False

        response = client.post(
            "/api/auth/login",
            json={"email": cfg.DEMO_USER_EMAIL, "password": "!"},
        )

        assert response.status_code == 401

    def test_demo_login_works_with_a_password(
        self, short, db_session, client, monkeypatch
    ):
        monkeypatch.setenv(DEMO_PASSWORD_ENV, "test-only-demo-password")

        loaded = load(db_session, short)

        assert loaded.demo_login_enabled is True

        response = client.post(
            "/api/auth/login",
            json={
                "email": cfg.DEMO_USER_EMAIL,
                "password": "test-only-demo-password",
            },
        )

        assert response.status_code == 200
        assert db_session.query(User).one().hashed_password != (
            "test-only-demo-password"
        )


class TestExport:
    def _read(self, path):
        with path.open(encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))

    def test_files_match_the_database(self, short, db_session, tmp_path):
        loaded = load(db_session, short)
        counts = export_dataset(
            db_session, loaded.business_id, short, tmp_path
        )

        sales = self._read(tmp_path / "sales.csv")
        items = self._read(tmp_path / "sale_items.csv")
        movements = self._read(tmp_path / "stock_movements.csv")
        products = self._read(tmp_path / "products.csv")

        assert len(sales) == db_session.query(Sale).count() == counts["sales"]
        assert len(movements) == db_session.query(StockMovement).count()
        assert len(products) == 75

        # Referential integrity inside the files themselves.
        sale_ids = {row["id"] for row in sales}
        product_ids = {row["id"] for row in products}

        assert {row["sale_id"] for row in items} <= sale_ids
        assert {row["product_id"] for row in items} <= product_ids
        assert {row["product_id"] for row in movements} <= product_ids

        # Sale totals equal the sum of their lines.
        totals = defaultdict(Decimal)

        for row in items:
            totals[row["sale_id"]] += Decimal(row["subtotal"])

        for row in sales:
            assert Decimal(row["total_amount"]) == totals[row["id"]]

    def test_values_are_formatted_consistently(
        self, short, db_session, tmp_path
    ):
        loaded = load(db_session, short)
        export_dataset(db_session, loaded.business_id, short, tmp_path)

        product = self._read(tmp_path / "products.csv")[0]
        movement = self._read(tmp_path / "stock_movements.csv")[0]

        assert len(product["sale_price"].split(".")[1]) == 2
        assert len(product["average_cost"].split(".")[1]) == 4
        assert len(movement["unit_cost"].split(".")[1]) == 4
        assert movement["created_at"].endswith("Z")
        assert product["is_active"] == "true"

    def test_manifest_labels_the_data_as_synthetic(
        self, short, db_session, tmp_path
    ):
        loaded = load(db_session, short)
        export_dataset(db_session, loaded.business_id, short, tmp_path)

        manifest = json.loads(
            (tmp_path / "manifest.json").read_text(encoding="utf-8")
        )

        assert manifest["synthetic"] is True
        assert manifest["seed"] == cfg.DEFAULT_SEED
        assert manifest["costing_method"] == "moving weighted average cost"
        assert manifest["scenarios"]["bulk_purchases"]
        assert manifest["row_counts"]["products"] == 75

    def test_ground_truth_is_kept_separate(self, short, db_session, tmp_path):
        loaded = load(db_session, short)
        export_dataset(db_session, loaded.business_id, short, tmp_path)

        truth = self._read(tmp_path / "ground_truth" / "daily_demand.csv")

        assert len(truth) == len(short.daily_truth)
        assert "lost_units" in truth[0]
        assert not (tmp_path / "daily_demand.csv").exists()

    def test_regenerating_gives_byte_identical_files(
        self, short, db_session, tmp_path
    ):
        first_dir = tmp_path / "first"
        second_dir = tmp_path / "second"

        loaded = load(db_session, short)
        export_dataset(db_session, loaded.business_id, short, first_dir)

        again = simulate(default_config(end=SHORT_END))
        reloaded = load(db_session, again, reset=True)
        db_session.expire_all()
        export_dataset(db_session, reloaded.business_id, again, second_dir)

        names = sorted(
            path.relative_to(first_dir).as_posix()
            for path in first_dir.rglob("*")
            if path.is_file()
        )

        assert len(names) == 10

        for name in names:
            assert (first_dir / name).read_bytes() == (
                second_dir / name
            ).read_bytes(), name
