"""Day-by-day simulation of the shop.

Pure Python with no database access: the same configuration and seed
always produce the same list of events. ``loader`` later replays
those events through the application's own services.

One simulated day, in order:

1. supplier cost changes take effect; sale prices follow later
2. new products are introduced
3. deliveries arrive before opening
4. customers arrive; each product's demand is drawn at random and
   capped by the stock on hand (the rest is lost, not backordered)
5. earlier sales are returned
6. on the last day of a month, a stock count finds small differences
7. in the evening the owner reorders products at or below minimum

Stock therefore can never go negative, and every unit sold was
physically available at opening time that day.
"""
import calendar
import math
import random
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from zoneinfo import ZoneInfo

from stockwise.datagen import config as cfg
from stockwise.datagen.config import (
    CategorySpec,
    ProductSpec,
    SimulationConfig,
)


CENT = Decimal("0.01")

# ------------------------------------------------------------------ events


@dataclass(frozen=True)
class ProductCreated:
    at: datetime
    sku: str
    name: str
    category: str
    supplier: str
    cost: Decimal
    price: Decimal
    minimum_stock: int
    opening_stock: int


@dataclass(frozen=True)
class PriceChanged:
    at: datetime
    sku: str
    price: Decimal


@dataclass(frozen=True)
class StockReceived:
    at: datetime
    sku: str
    quantity: int
    unit_cost: Decimal
    note: str


@dataclass(frozen=True)
class SaleMade:
    at: datetime
    ref: int
    lines: tuple[tuple[str, int], ...]


@dataclass(frozen=True)
class ReturnMade:
    at: datetime
    sale_ref: int
    sku: str
    quantity: int
    reason: str


@dataclass(frozen=True)
class StockAdjusted:
    at: datetime
    sku: str
    movement_type: str
    quantity: int
    note: str


Event = (
    ProductCreated
    | PriceChanged
    | StockReceived
    | SaleMade
    | ReturnMade
    | StockAdjusted
)


@dataclass(frozen=True)
class DailyTruth:
    """What really happened to one product on one day.

    ``lost_units`` is demand the shop could not serve because it had
    run out. A real shop never observes this number, so it is kept
    out of the database and exported separately, to check later
    estimates of lost sales against.
    """
    day: date
    sku: str
    demand_units: int
    sold_units: int
    lost_units: int
    opening_stock: int
    closing_stock: int


@dataclass(frozen=True)
class ProductPolicy:
    """The fixed purchasing rule the owner uses for one product."""
    sku: str
    base_daily_demand: float
    yearly_trend: float
    minimum_stock: int
    order_quantity: int
    opening_stock: int


@dataclass
class SimulationResult:
    config: SimulationConfig
    events: list[Event]
    daily_truth: list[DailyTruth]
    policies: dict[str, ProductPolicy]

    @property
    def demand_units(self) -> int:
        return sum(row.demand_units for row in self.daily_truth)

    @property
    def sold_units(self) -> int:
        return sum(row.sold_units for row in self.daily_truth)

    @property
    def lost_units(self) -> int:
        return sum(row.lost_units for row in self.daily_truth)

    @property
    def fill_rate(self) -> float:
        demand = self.demand_units

        return self.sold_units / demand if demand else 1.0


# ----------------------------------------------------------- pure helpers


def money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def shelf_price(value: Decimal) -> Decimal:
    """Round to the nearest 0.50, the way shelf prices are set."""
    return (value * 2).quantize(Decimal("1"), rounding=ROUND_HALF_UP) / 2


def month_factor(category: CategorySpec, day: date) -> float:
    """Seasonal multiplier, blended linearly between mid-months.

    Using the raw monthly value would make demand jump on the first
    of each month. Each month's value is treated as its mid-month
    level and days in between are interpolated.
    """
    factors = category.month_factors
    days_in_month = calendar.monthrange(day.year, day.month)[1]
    position = (day.day - 0.5) / days_in_month

    current = factors[day.month - 1]

    if position < 0.5:
        neighbour = factors[(day.month - 2) % 12]
        weight = 0.5 + position
    else:
        neighbour = factors[day.month % 12]
        weight = 1.5 - position

    return weight * current + (1 - weight) * neighbour


def poisson(rng: random.Random, rate: float) -> int:
    """Draw a count of arrivals for an average of ``rate``."""
    if rate <= 0:
        return 0

    if rate >= 30:
        # Normal approximation; exact sampling gets slow and
        # numerically fragile for large rates.
        return max(0, round(rng.gauss(rate, math.sqrt(rate))))

    # Knuth's method.
    threshold = math.exp(-rate)
    count = 0
    product = rng.random()

    while product > threshold:
        count += 1
        product *= rng.random()

    return count


def _pick(rng: random.Random, weights: dict[int, int]) -> int:
    return rng.choices(list(weights), weights=list(weights.values()))[0]


def purchasing_policy(
    spec: ProductSpec,
    *,
    base_daily_demand: float,
    yearly_trend: float,
    lead_time_days: int,
) -> ProductPolicy:
    minimum_stock = max(
        cfg.MINIMUM_MINIMUM_STOCK,
        math.ceil(base_daily_demand * (lead_time_days + cfg.SAFETY_DAYS)),
    )

    packs = math.ceil(
        base_daily_demand * cfg.ORDER_COVER_DAYS / cfg.ORDER_PACK_SIZE
    )
    order_quantity = max(1, packs) * cfg.ORDER_PACK_SIZE

    return ProductPolicy(
        sku=spec.sku,
        base_daily_demand=base_daily_demand,
        yearly_trend=yearly_trend,
        minimum_stock=minimum_stock,
        order_quantity=order_quantity,
        opening_stock=minimum_stock + order_quantity,
    )


# ------------------------------------------------------------------ state


@dataclass
class _ProductState:
    spec: ProductSpec
    policy: ProductPolicy
    supplier_cost: Decimal
    sale_price: Decimal
    stock: int = 0
    on_order: int = 0
    created: bool = False


class _DayClock:
    """Hands out timestamps for one day, never the same one twice.

    Unique timestamps give every product's movements a strict order,
    which the ledger checks rely on.
    """

    def __init__(self, day: date, tz: ZoneInfo) -> None:
        self._day = day
        self._tz = tz
        self._used: set[datetime] = set()

    def at(self, hour: int, minute: int = 0, second: int = 0) -> datetime:
        local = datetime.combine(self._day, time(hour, minute, second))

        while local in self._used:
            local += timedelta(seconds=1)

        self._used.add(local)

        return local.replace(tzinfo=self._tz).astimezone(timezone.utc)

    def during_opening_hours(self, rng: random.Random) -> datetime:
        offset = rng.choices(
            range(len(cfg.HOURLY_WEIGHTS)),
            weights=cfg.HOURLY_WEIGHTS,
        )[0]

        return self.at(
            cfg.OPENING_HOUR + offset,
            rng.randrange(60),
            rng.randrange(60),
        )


def demand_rate(
    state_or_spec,
    *,
    policy: ProductPolicy,
    category: CategorySpec,
    day: date,
    config: SimulationConfig,
) -> float:
    """Expected units demanded for one product on one day."""
    spec: ProductSpec = getattr(state_or_spec, "spec", state_or_spec)

    rate = policy.base_daily_demand

    if spec.velocity == "D":
        rate *= cfg.DEAD_STOCK_DEMAND_FACTOR

    rate *= month_factor(category, day)
    rate *= category.weekday_factors[day.weekday()]

    years_elapsed = (day - config.start).days / 365
    rate *= max(0.0, 1 + policy.yearly_trend * years_elapsed)

    if spec.fade_from is not None and day >= spec.fade_from:
        days_fading = (day - spec.fade_from).days + 1
        rate *= math.exp(-days_fading / cfg.FADE_DECAY_DAYS)

    for special in config.special_days:
        if special.on == day and (
            special.categories is None
            or spec.category in special.categories
        ):
            rate *= special.factor

    for spike in config.demand_spikes:
        if spike.sku == spec.sku and spike.start <= day <= spike.end:
            rate *= spike.multiplier

    return rate


# ------------------------------------------------------------- simulation


def simulate(config: SimulationConfig) -> SimulationResult:
    rng = random.Random(config.seed)
    tz = ZoneInfo(config.timezone)

    categories = {category.key: category for category in config.categories}
    suppliers = {supplier.key: supplier for supplier in config.suppliers}

    # Per-product parameters are drawn first, in catalogue order, so
    # they do not depend on how long the simulated period is.
    states: dict[str, _ProductState] = {}

    for spec in config.products:
        low, high = cfg.VELOCITY_RATE_RANGES[spec.velocity]
        base_daily_demand = rng.uniform(low, high)
        yearly_trend = rng.uniform(*cfg.YEARLY_TREND_RANGE)

        states[spec.sku] = _ProductState(
            spec=spec,
            policy=purchasing_policy(
                spec,
                base_daily_demand=base_daily_demand,
                yearly_trend=yearly_trend,
                lead_time_days=suppliers[spec.supplier].lead_time_days,
            ),
            supplier_cost=spec.cost,
            sale_price=spec.price,
        )

    events: list[Event] = []
    daily_truth: list[DailyTruth] = []

    deliveries: dict[date, list[tuple[str, int, Decimal]]] = defaultdict(list)
    returns_due: dict[date, list[tuple[int, str, int, str]]] = (
        defaultdict(list)
    )
    price_follow: dict[date, list[cfg.CostChange]] = defaultdict(list)

    sale_ref = 0
    day = config.start

    while day <= config.end:
        clock = _DayClock(day, tz)

        # 1. Supplier cost changes; sale prices follow later.
        for change in config.cost_changes:
            if change.on != day:
                continue

            for state in states.values():
                if state.spec.supplier == change.supplier:
                    state.supplier_cost = money(
                        state.supplier_cost
                        * Decimal(str(1 + change.percent))
                    )

            price_follow[
                day + timedelta(days=cfg.PRICE_FOLLOW_DAYS)
            ].append(change)

        for change in price_follow.pop(day, ()):
            for state in states.values():
                if state.spec.supplier != change.supplier:
                    continue

                new_price = shelf_price(
                    state.sale_price * Decimal(str(1 + change.percent))
                )

                if new_price == state.sale_price:
                    continue

                state.sale_price = new_price

                if state.created:
                    events.append(
                        PriceChanged(
                            at=clock.at(7, 0),
                            sku=state.spec.sku,
                            price=new_price,
                        )
                    )

        # 2. Product launches (every initial product on day one).
        for state in states.values():
            launch_day = max(state.spec.launch or config.start, config.start)

            if state.created or launch_day != day:
                continue

            state.created = True
            state.stock = state.policy.opening_stock

            events.append(
                ProductCreated(
                    at=clock.at(7, 30),
                    sku=state.spec.sku,
                    name=state.spec.name,
                    category=state.spec.category,
                    supplier=state.spec.supplier,
                    cost=state.supplier_cost,
                    price=state.sale_price,
                    minimum_stock=state.policy.minimum_stock,
                    opening_stock=state.policy.opening_stock,
                )
            )

        # 3. Stock arriving before opening.
        for bulk in config.bulk_purchases:
            state = states.get(bulk.sku)

            if bulk.on != day or state is None or not state.created:
                continue

            state.stock += bulk.quantity

            events.append(
                StockReceived(
                    at=clock.at(8, 0),
                    sku=bulk.sku,
                    quantity=bulk.quantity,
                    unit_cost=money(
                        state.supplier_cost
                        * Decimal(str(1 - bulk.discount_percent / 100))
                    ),
                    note=bulk.label,
                )
            )

        for sku, quantity, unit_cost in deliveries.pop(day, ()):
            state = states[sku]
            state.stock += quantity
            state.on_order -= quantity

            events.append(
                StockReceived(
                    at=clock.at(8, 0),
                    sku=sku,
                    quantity=quantity,
                    unit_cost=unit_cost,
                    note="Tedarikçi teslimatı",
                )
            )

        opening_stock = {
            sku: state.stock
            for sku, state in states.items()
            if state.created
        }

        # 4. Customers. Demand beyond the stock on hand is lost.
        demanded: dict[str, int] = {}
        sold: dict[str, int] = {}
        lines: list[tuple[str, int]] = []

        for sku, state in states.items():
            if not state.created:
                continue

            demand = poisson(
                rng,
                demand_rate(
                    state,
                    policy=state.policy,
                    category=categories[state.spec.category],
                    day=day,
                    config=config,
                ),
            )
            units = min(demand, state.stock)

            state.stock -= units
            demanded[sku] = demand
            sold[sku] = units

            remaining = units

            while remaining > 0:
                quantity = min(
                    remaining,
                    _pick(rng, cfg.LINE_QUANTITY_WEIGHTS),
                )
                lines.append((sku, quantity))
                remaining -= quantity

        rng.shuffle(lines)

        index = 0

        while index < len(lines):
            size = _pick(rng, cfg.BASKET_LINE_WEIGHTS)
            basket: dict[str, int] = {}

            for sku, quantity in lines[index:index + size]:
                basket[sku] = basket.get(sku, 0) + quantity

            index += size
            sale_ref += 1

            events.append(
                SaleMade(
                    at=clock.during_opening_hours(rng),
                    ref=sale_ref,
                    lines=tuple(basket.items()),
                )
            )

            for sku, quantity in basket.items():
                category = categories[states[sku].spec.category]

                if rng.random() >= category.return_rate:
                    continue

                due = day + timedelta(
                    days=rng.randint(1, cfg.MAX_RETURN_DELAY_DAYS)
                )
                returned = 1 if quantity == 1 else rng.randint(1, quantity)
                reason = rng.choice(cfg.RETURN_REASONS)

                if due <= config.end:
                    returns_due[due].append(
                        (sale_ref, sku, returned, reason)
                    )

        # 5. Returns of earlier sales.
        for ref, sku, quantity, reason in returns_due.pop(day, ()):
            states[sku].stock += quantity

            events.append(
                ReturnMade(
                    at=clock.during_opening_hours(rng),
                    sale_ref=ref,
                    sku=sku,
                    quantity=quantity,
                    reason=reason,
                )
            )

        # 6. Month-end stock count.
        if (day + timedelta(days=1)).month != day.month:
            for sku, state in states.items():
                if not state.created or state.stock <= 0:
                    continue

                roll = rng.random()

                if roll < cfg.SHRINKAGE_PROBABILITY:
                    quantity = rng.randint(
                        1,
                        min(cfg.MAX_SHRINKAGE_UNITS, state.stock),
                    )
                    state.stock -= quantity
                    movement_type = "ADJUSTMENT_OUT"
                elif roll < (
                    cfg.SHRINKAGE_PROBABILITY + cfg.SURPLUS_PROBABILITY
                ):
                    quantity = rng.randint(1, 2)
                    state.stock += quantity
                    movement_type = "ADJUSTMENT_IN"
                else:
                    continue

                events.append(
                    StockAdjusted(
                        at=clock.at(21, 30),
                        sku=sku,
                        movement_type=movement_type,
                        quantity=quantity,
                        note="Ay sonu sayım farkı",
                    )
                )

        # 7. Evening reorder, except Sundays.
        if day.weekday() != 6:
            for sku, state in states.items():
                if not state.created:
                    continue

                if state.stock + state.on_order > state.policy.minimum_stock:
                    continue

                supplier = suppliers[state.spec.supplier]

                extra_days = rng.choices(
                    [days for days, _ in cfg.RANDOM_DELIVERY_DELAYS],
                    weights=[
                        weight for _, weight in cfg.RANDOM_DELIVERY_DELAYS
                    ],
                )[0]

                for delay in config.supplier_delays:
                    if (
                        delay.supplier == supplier.key
                        and delay.start <= day <= delay.end
                    ):
                        extra_days += delay.extra_days

                arrival = day + timedelta(
                    days=max(1, supplier.lead_time_days + extra_days)
                )

                state.on_order += state.policy.order_quantity

                if arrival <= config.end:
                    deliveries[arrival].append(
                        (
                            sku,
                            state.policy.order_quantity,
                            state.supplier_cost,
                        )
                    )

        for sku, opening in opening_stock.items():
            daily_truth.append(
                DailyTruth(
                    day=day,
                    sku=sku,
                    demand_units=demanded[sku],
                    sold_units=sold[sku],
                    lost_units=demanded[sku] - sold[sku],
                    opening_stock=opening,
                    closing_stock=states[sku].stock,
                )
            )

        day += timedelta(days=1)

    events.sort(key=lambda event: event.at)

    return SimulationResult(
        config=config,
        events=events,
        daily_truth=daily_truth,
        policies={sku: state.policy for sku, state in states.items()},
    )
