from datetime import datetime, timezone
from decimal import Decimal

import pytest

from stockwise.app.models.sale_item import SaleItem
from stockwise.app.models.stock_movement import StockMovement
from stockwise.app.services.inventory import (
    InsufficientStockError,
    apply_stock_change,
    lock_products,
)
from stockwise.app.services.sales import (
    DuplicateProductError,
    ProductNotFoundError,
    create_sale,
)
from tests.test_sales import _create_product, _create_user_and_business


PAST = datetime(2025, 3, 14, 10, 30, tzinfo=timezone.utc)


def _as_utc(value: datetime) -> datetime:
    # SQLite returns naive datetimes.
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


class TestApplyStockChange:
    def test_inbound_increases_stock_and_records_levels(self, db_session):
        _, business = _create_user_and_business(db_session)
        product = _create_product(db_session, business, stock=4)

        movement = apply_stock_change(
            db_session,
            product=product,
            movement_type="IN",
            quantity=6,
            note="delivery",
        )
        db_session.commit()

        assert product.stock_quantity == 10
        assert (movement.stock_before, movement.stock_after) == (4, 10)
        assert movement.business_id == business.id

    def test_outbound_cannot_go_below_zero(self, db_session):
        _, business = _create_user_and_business(db_session)
        product = _create_product(db_session, business, stock=2)

        with pytest.raises(InsufficientStockError):
            apply_stock_change(
                db_session,
                product=product,
                movement_type="OUT",
                quantity=3,
            )

        assert product.stock_quantity == 2
        assert db_session.query(StockMovement).count() == 0

    @pytest.mark.parametrize("quantity", [0, -1])
    def test_non_positive_quantity_rejected(self, db_session, quantity):
        _, business = _create_user_and_business(db_session)
        product = _create_product(db_session, business)

        with pytest.raises(ValueError):
            apply_stock_change(
                db_session,
                product=product,
                movement_type="IN",
                quantity=quantity,
            )

    def test_unknown_movement_type_rejected(self, db_session):
        _, business = _create_user_and_business(db_session)
        product = _create_product(db_session, business)

        with pytest.raises(ValueError):
            apply_stock_change(
                db_session,
                product=product,
                movement_type="TELEPORT",
                quantity=1,
            )

    def test_movement_can_be_backdated(self, db_session):
        _, business = _create_user_and_business(db_session)
        product = _create_product(db_session, business)

        movement = apply_stock_change(
            db_session,
            product=product,
            movement_type="IN",
            quantity=1,
            at=PAST,
        )
        db_session.commit()
        db_session.refresh(movement)

        assert _as_utc(movement.created_at) == PAST


class TestLockProducts:
    def test_excludes_other_business_and_inactive(self, db_session):
        _, business = _create_user_and_business(db_session)
        _, other_business = _create_user_and_business(db_session)

        own = _create_product(db_session, business)
        inactive = _create_product(db_session, business)
        inactive.is_active = False
        foreign = _create_product(db_session, other_business)
        db_session.commit()

        ids = [own.id, inactive.id, foreign.id]

        assert set(
            lock_products(
                db_session,
                business_id=business.id,
                product_ids=ids,
            )
        ) == {own.id}

        assert set(
            lock_products(
                db_session,
                business_id=business.id,
                product_ids=ids,
                active_only=False,
            )
        ) == {own.id, inactive.id}


class TestCreateSale:
    def test_writes_sale_items_and_movements(self, db_session):
        _, business = _create_user_and_business(db_session)
        first = _create_product(db_session, business, stock=10)
        second = _create_product(db_session, business, stock=5)

        sale = create_sale(
            db_session,
            business_id=business.id,
            items=[(first.id, 3), (second.id, 5)],
        )
        db_session.commit()

        assert first.stock_quantity == 7
        assert second.stock_quantity == 0
        assert (
            db_session.query(SaleItem)
            .filter(SaleItem.sale_id == sale.id)
            .count()
            == 2
        )
        assert (
            db_session.query(StockMovement)
            .filter(StockMovement.movement_type == "SALE")
            .count()
            == 2
        )
        assert Decimal(sale.gross_profit) == (
            Decimal(sale.total_amount) - Decimal(sale.total_cost)
        )

    def test_backdated_sale_and_movements_share_timestamp(self, db_session):
        _, business = _create_user_and_business(db_session)
        product = _create_product(db_session, business)

        sale = create_sale(
            db_session,
            business_id=business.id,
            items=[(product.id, 1)],
            at=PAST,
        )
        db_session.commit()
        db_session.refresh(sale)

        movement = db_session.query(StockMovement).one()

        assert _as_utc(sale.created_at) == PAST
        assert _as_utc(movement.created_at) == PAST

    def test_short_line_leaves_all_stock_untouched(self, db_session):
        _, business = _create_user_and_business(db_session)
        plenty = _create_product(db_session, business, stock=10)
        short = _create_product(db_session, business, stock=1)

        with pytest.raises(InsufficientStockError):
            create_sale(
                db_session,
                business_id=business.id,
                items=[(plenty.id, 2), (short.id, 2)],
            )

        db_session.rollback()

        assert plenty.stock_quantity == 10
        assert short.stock_quantity == 1

    def test_duplicate_and_unknown_products_rejected(self, db_session):
        _, business = _create_user_and_business(db_session)
        _, other_business = _create_user_and_business(db_session)
        product = _create_product(db_session, business)
        foreign = _create_product(db_session, other_business)

        with pytest.raises(DuplicateProductError):
            create_sale(
                db_session,
                business_id=business.id,
                items=[(product.id, 1), (product.id, 1)],
            )

        with pytest.raises(ProductNotFoundError):
            create_sale(
                db_session,
                business_id=business.id,
                items=[(foreign.id, 1)],
            )
