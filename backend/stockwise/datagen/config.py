"""Every assumption behind the synthetic dataset lives in this file.

The dataset describes one fictional small general retail shop in
Istanbul. Nothing here is real data. Change a value, regenerate, and
the whole history changes consistently.

Money is in Turkish lira. Dates are local (Europe/Istanbul).
"""
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

DEFAULT_SEED = 42

# Fifteen months. August to October is covered twice, which allows a
# year-over-year comparison for those months.
DEFAULT_START = date(2025, 8, 1)
DEFAULT_END = date(2026, 10, 31)

TIMEZONE = "Europe/Istanbul"

DEMO_USER_EMAIL = "demo@stockwise.example"
DEMO_USER_NAME = "Demo Kullanıcı"
DEMO_BUSINESS_NAME = "Demo Market (sentetik veri)"

# Shop hours, local time. Weights give the relative share of sales in
# each hour starting at OPENING_HOUR: a lunch bump and an evening peak.
OPENING_HOUR = 9
HOURLY_WEIGHTS = (3, 4, 5, 7, 8, 6, 5, 6, 8, 9, 7, 4)

# How many lines a basket has, and how many units a line has.
BASKET_LINE_WEIGHTS = {1: 50, 2: 28, 3: 14, 4: 8}
LINE_QUANTITY_WEIGHTS = {1: 75, 2: 20, 3: 5}

# Average units sold per day, by velocity class. Each product draws
# its own base rate from the range of its class.
#   A fast movers, B regular, C slow movers,
#   D products the owner expected to sell like a regular product
#     but which barely sell at all.
VELOCITY_RATE_RANGES = {
    "A": (2.5, 6.0),
    "B": (0.8, 2.2),
    "C": (0.15, 0.6),
    "D": (0.5, 1.5),
}

# A class D product actually sells at this fraction of the rate the
# owner planned for.
DEAD_STOCK_DEMAND_FACTOR = 0.06

# Each product also drifts up or down over the year by a factor drawn
# from this range (-15% to +20% per year).
YEARLY_TREND_RANGE = (-0.15, 0.20)

# After a product's fade date its demand decays with this half-life
# style constant (days). After about three months it is close to zero.
FADE_DECAY_DAYS = 20.0

# --- The owner's purchasing policy -----------------------------------
#
# Deliberately naive. Each product gets a fixed minimum stock and a
# fixed order quantity, worked out once from the sales the owner
# expects on an average day. Every evening except Sunday the owner
# orders the fixed quantity for any product at or below its minimum.
# The policy never adapts to season, trend or actual sales, which is
# what produces both stockouts and overstock in the history.
SAFETY_DAYS = 2           # minimum covers lead time + this many days
ORDER_COVER_DAYS = 14     # one order covers this many average days
ORDER_PACK_SIZE = 6       # orders are rounded up to full packs
MINIMUM_MINIMUM_STOCK = 2

# Supplier deliveries are sometimes late: (extra days, probability).
RANDOM_DELIVERY_DELAYS = ((0, 0.85), (1, 0.10), (2, 0.04), (4, 0.01))

# Sale prices follow a supplier cost increase after this many days,
# so margins are squeezed in between.
PRICE_FOLLOW_DAYS = 21

# Returns happen 1 to this many days after the sale.
MAX_RETURN_DELAY_DAYS = 10
RETURN_REASONS = (
    "Hasarlı ürün",
    "Kusurlu ürün",
    "Müşteri vazgeçti",
    "Yanlış ürün alınmış",
)

# Month-end stock count. Chance that a product with stock shows
# shrinkage (loss, damage, theft) or a small surplus.
SHRINKAGE_PROBABILITY = 0.12
SURPLUS_PROBABILITY = 0.02
MAX_SHRINKAGE_UNITS = 3


@dataclass(frozen=True)
class SupplierSpec:
    key: str
    name: str
    lead_time_days: int


@dataclass(frozen=True)
class CategorySpec:
    key: str
    name: str
    # Demand multiplier for January..December. 1.0 is an average month.
    month_factors: tuple[float, ...]
    # Demand multiplier for Monday..Sunday.
    weekday_factors: tuple[float, ...]
    # Probability that a sold line is later returned.
    return_rate: float


@dataclass(frozen=True)
class ProductSpec:
    sku: str
    name: str
    category: str
    supplier: str
    cost: Decimal
    price: Decimal
    velocity: str
    # Product is introduced on this date instead of the first day.
    launch: date | None = None
    # Demand collapses from this date on.
    fade_from: date | None = None


@dataclass(frozen=True)
class CostChange:
    """A supplier raises (or lowers) all its prices by ``percent``."""
    supplier: str
    on: date
    percent: float


@dataclass(frozen=True)
class SpecialDay:
    """A day on which demand differs from the usual pattern."""
    on: date
    factor: float
    label: str
    # None applies to every category.
    categories: tuple[str, ...] | None = None


@dataclass(frozen=True)
class SupplierDelay:
    """Orders placed with a supplier in this window arrive late."""
    supplier: str
    start: date
    end: date
    extra_days: int
    label: str


@dataclass(frozen=True)
class BulkPurchase:
    """A one-off large purchase outside the normal policy."""
    sku: str
    on: date
    quantity: int
    discount_percent: float
    label: str


@dataclass(frozen=True)
class DemandSpike:
    """A short burst of unusually high demand for one product."""
    sku: str
    start: date
    end: date
    multiplier: float
    label: str


@dataclass(frozen=True)
class SimulationConfig:
    seed: int = DEFAULT_SEED
    start: date = DEFAULT_START
    end: date = DEFAULT_END
    timezone: str = TIMEZONE
    suppliers: tuple[SupplierSpec, ...] = ()
    categories: tuple[CategorySpec, ...] = ()
    products: tuple[ProductSpec, ...] = ()
    cost_changes: tuple[CostChange, ...] = ()
    special_days: tuple[SpecialDay, ...] = ()
    supplier_delays: tuple[SupplierDelay, ...] = ()
    bulk_purchases: tuple[BulkPurchase, ...] = ()
    demand_spikes: tuple[DemandSpike, ...] = ()


# ---------------------------------------------------------------------
# Suppliers
# ---------------------------------------------------------------------

SUPPLIERS = (
    SupplierSpec("icecek", "Marmara İçecek Dağıtım", 2),
    SupplierSpec("gida", "Anadolu Gıda Toptan", 3),
    SupplierSpec("kirtasiye", "Kalem Kırtasiye Ltd.", 5),
    SupplierSpec("temizlik", "Temiz Ev Ürünleri A.Ş.", 7),
    SupplierSpec("oyuncak", "Oyun Dünyası İthalat", 14),
    SupplierSpec("tekno", "TeknoAksesuar İthalat", 21),
)

# ---------------------------------------------------------------------
# Categories and their demand patterns
# ---------------------------------------------------------------------

FLAT_YEAR = (1.0,) * 12

CATEGORIES = (
    CategorySpec(
        "beverages",
        "İçecek",
        # Strong summer peak.
        (0.70, 0.70, 0.80, 0.95, 1.15, 1.40,
         1.60, 1.60, 1.25, 0.95, 0.75, 0.75),
        (0.90, 0.90, 0.95, 1.00, 1.10, 1.30, 1.20),
        0.005,
    ),
    CategorySpec(
        "snacks",
        "Atıştırmalık",
        (1.00, 1.00, 1.00, 1.00, 1.00, 0.95,
         0.90, 0.90, 1.05, 1.05, 1.05, 1.15),
        (0.90, 0.90, 0.95, 1.00, 1.10, 1.25, 1.15),
        0.005,
    ),
    CategorySpec(
        "stationery",
        "Kırtasiye",
        # Back to school in September, second term in February.
        (0.90, 1.30, 0.80, 0.70, 0.70, 0.50,
         0.40, 0.90, 2.60, 1.30, 0.90, 0.80),
        # Bought on school days, not weekends.
        (1.15, 1.10, 1.10, 1.05, 1.00, 0.80, 0.60),
        0.015,
    ),
    CategorySpec(
        "cleaning",
        "Ev Temizliği",
        # Mild spring-cleaning bump.
        (1.00, 1.00, 1.05, 1.15, 1.10, 1.00,
         0.95, 0.95, 1.00, 1.00, 1.00, 1.00),
        (0.95, 0.95, 1.00, 1.00, 1.05, 1.15, 1.00),
        0.010,
    ),
    CategorySpec(
        "personal_care",
        "Kişisel Bakım",
        FLAT_YEAR,
        (0.95, 0.95, 1.00, 1.00, 1.05, 1.15, 1.05),
        0.015,
    ),
    CategorySpec(
        "winter",
        "Kışlık Ürünler",
        # Almost nothing sells in summer.
        (1.80, 1.40, 0.70, 0.30, 0.15, 0.10,
         0.10, 0.15, 0.40, 1.00, 1.90, 2.30),
        (0.90, 0.90, 0.95, 1.00, 1.05, 1.30, 1.20),
        0.030,
    ),
    CategorySpec(
        "toys",
        "Oyuncak ve Hediyelik",
        # New Year gifts in December, Children's Day in April.
        (0.80, 0.90, 0.80, 1.10, 0.90, 1.00,
         1.00, 0.90, 0.80, 0.90, 1.20, 2.80),
        (0.80, 0.80, 0.85, 0.90, 1.10, 1.50, 1.40),
        0.030,
    ),
    CategorySpec(
        "phone",
        "Telefon Aksesuarı",
        FLAT_YEAR,
        (0.95, 0.95, 1.00, 1.00, 1.05, 1.10, 1.05),
        0.060,
    ),
)

# ---------------------------------------------------------------------
# Products
# ---------------------------------------------------------------------


def _p(sku, name, category, supplier, cost, price, velocity, **extra):
    return ProductSpec(
        sku=sku,
        name=name,
        category=category,
        supplier=supplier,
        cost=Decimal(cost),
        price=Decimal(price),
        velocity=velocity,
        **extra,
    )


PRODUCTS = (
    # --- İçecek ---------------------------------------------------
    _p("BEV-001", "Su 0.5L", "beverages", "icecek", "3.50", "7.50", "A"),
    _p("BEV-002", "Su 1.5L", "beverages", "icecek", "6.00", "12.50", "A"),
    _p("BEV-003", "Maden Suyu 200ml", "beverages", "icecek",
       "5.00", "10.00", "A"),
    _p("BEV-004", "Kola 330ml", "beverages", "icecek",
       "18.00", "30.00", "A"),
    _p("BEV-005", "Kola 1L", "beverages", "icecek", "30.00", "47.50", "B"),
    _p("BEV-006", "Meyve Suyu 1L", "beverages", "icecek",
       "28.00", "45.00", "B"),
    _p("BEV-007", "Soğuk Çay 500ml", "beverages", "icecek",
       "16.00", "27.50", "B"),
    _p("BEV-008", "Ayran 300ml", "beverages", "icecek",
       "9.00", "16.00", "B"),
    _p("BEV-009", "Enerji İçeceği 250ml", "beverages", "icecek",
       "32.00", "52.50", "C"),
    _p("BEV-010", "Limonata 1L", "beverages", "icecek",
       "26.00", "42.50", "C", launch=date(2026, 5, 1)),

    # --- Atıştırmalık ---------------------------------------------
    _p("SNK-001", "Cips 110g", "snacks", "gida", "22.00", "37.50", "A"),
    _p("SNK-002", "Çikolata 60g", "snacks", "gida", "18.00", "30.00", "A"),
    _p("SNK-003", "Bisküvi 100g", "snacks", "gida", "9.00", "16.00", "A"),
    _p("SNK-004", "Kraker 150g", "snacks", "gida", "12.00", "20.00", "B"),
    _p("SNK-005", "Gofret 40g", "snacks", "gida", "8.00", "14.00", "B"),
    _p("SNK-006", "Kuruyemiş 150g", "snacks", "gida",
       "55.00", "85.00", "B"),
    _p("SNK-007", "Sakız", "snacks", "gida", "7.00", "12.50", "B"),
    _p("SNK-008", "Protein Bar", "snacks", "gida",
       "35.00", "55.00", "C", launch=date(2026, 2, 1)),
    _p("SNK-009", "Glutensiz Bisküvi", "snacks", "gida",
       "30.00", "50.00", "D"),
    _p("SNK-010", "Şekerleme 150g", "snacks", "gida",
       "20.00", "32.50", "C"),

    # --- Kırtasiye ------------------------------------------------
    _p("STA-001", "Tükenmez Kalem", "stationery", "kirtasiye",
       "6.00", "12.50", "A"),
    _p("STA-002", "Kurşun Kalem", "stationery", "kirtasiye",
       "4.00", "8.50", "B"),
    _p("STA-003", "A4 Defter 80 Yaprak", "stationery", "kirtasiye",
       "28.00", "47.50", "A"),
    _p("STA-004", "Silgi", "stationery", "kirtasiye", "3.50", "8.00", "B"),
    _p("STA-005", "Kalemtıraş", "stationery", "kirtasiye",
       "5.00", "11.00", "C"),
    _p("STA-006", "Fosforlu Kalem", "stationery", "kirtasiye",
       "12.00", "22.50", "B"),
    _p("STA-007", "Yapıştırıcı", "stationery", "kirtasiye",
       "14.00", "25.00", "C"),
    _p("STA-008", "Plastik Dosya", "stationery", "kirtasiye",
       "10.00", "19.00", "B"),
    # A dated product: nobody buys a 2025 diary once the year is ending.
    _p("STA-009", "Ajanda 2025", "stationery", "kirtasiye",
       "60.00", "110.00", "B", fade_from=date(2025, 10, 1)),
    _p("STA-010", "Boya Kalemi 12'li", "stationery", "kirtasiye",
       "40.00", "69.00", "B"),

    # --- Ev Temizliği ---------------------------------------------
    _p("CLN-001", "Bulaşık Deterjanı 750ml", "cleaning", "temizlik",
       "38.00", "59.00", "B"),
    _p("CLN-002", "Çamaşır Suyu 1L", "cleaning", "temizlik",
       "22.00", "36.00", "B"),
    _p("CLN-003", "Yüzey Temizleyici 1L", "cleaning", "temizlik",
       "42.00", "65.00", "B"),
    _p("CLN-004", "Bulaşık Süngeri 5'li", "cleaning", "temizlik",
       "15.00", "27.50", "B"),
    _p("CLN-005", "Çöp Torbası 20'li", "cleaning", "temizlik",
       "18.00", "30.00", "A"),
    _p("CLN-006", "Kağıt Havlu 6'lı", "cleaning", "temizlik",
       "75.00", "115.00", "B"),
    _p("CLN-007", "Tuvalet Kağıdı 12'li", "cleaning", "temizlik",
       "110.00", "165.00", "B"),
    _p("CLN-008", "Cam Temizleyici", "cleaning", "temizlik",
       "35.00", "55.00", "C"),
    _p("CLN-009", "Oda Kokusu", "cleaning", "temizlik",
       "45.00", "75.00", "C", launch=date(2026, 1, 15)),
    _p("CLN-010", "Halı Şampuanı", "cleaning", "temizlik",
       "60.00", "95.00", "D"),

    # --- Kişisel Bakım --------------------------------------------
    _p("PRS-001", "Şampuan 400ml", "personal_care", "temizlik",
       "65.00", "99.00", "B"),
    _p("PRS-002", "Diş Macunu", "personal_care", "temizlik",
       "40.00", "62.50", "B"),
    _p("PRS-003", "Sabun 4'lü", "personal_care", "temizlik",
       "35.00", "55.00", "B"),
    _p("PRS-004", "Islak Mendil", "personal_care", "temizlik",
       "18.00", "30.00", "A"),
    _p("PRS-005", "Deodorant", "personal_care", "temizlik",
       "70.00", "110.00", "C"),
    _p("PRS-006", "El Kremi", "personal_care", "temizlik",
       "45.00", "72.50", "C"),
    _p("PRS-007", "Tıraş Köpüğü", "personal_care", "temizlik",
       "55.00", "85.00", "C"),
    _p("PRS-008", "Güneş Kremi", "personal_care", "temizlik",
       "120.00", "189.00", "C"),
    _p("PRS-009", "Saç Jölesi", "personal_care", "temizlik",
       "50.00", "80.00", "D"),
    _p("PRS-010", "Dudak Koruyucu", "personal_care", "temizlik",
       "25.00", "42.50", "C"),

    # --- Kışlık Ürünler -------------------------------------------
    _p("WIN-001", "Eldiven", "winter", "oyuncak", "60.00", "110.00", "B"),
    _p("WIN-002", "Bere", "winter", "oyuncak", "55.00", "99.00", "B"),
    _p("WIN-003", "Atkı", "winter", "oyuncak", "80.00", "145.00", "C"),
    _p("WIN-004", "Şemsiye", "winter", "oyuncak", "110.00", "189.00", "B"),
    _p("WIN-005", "Termos 500ml", "winter", "oyuncak",
       "140.00", "239.00", "C"),
    _p("WIN-006", "El Isıtıcı 2'li", "winter", "oyuncak",
       "20.00", "37.50", "B"),
    _p("WIN-007", "Yün Çorap", "winter", "oyuncak", "35.00", "62.50", "B"),
    _p("WIN-008", "Yağmurluk", "winter", "oyuncak",
       "90.00", "159.00", "C"),
    _p("WIN-009", "Buz Çözücü Sprey", "winter", "oyuncak",
       "50.00", "85.00", "D"),
    _p("WIN-010", "Polar Battaniye", "winter", "oyuncak",
       "150.00", "259.00", "C", launch=date(2025, 11, 1)),

    # --- Oyuncak ve Hediyelik -------------------------------------
    _p("TOY-001", "Oyun Kartı", "toys", "oyuncak", "25.00", "45.00", "B"),
    _p("TOY-002", "Balon 10'lu", "toys", "oyuncak", "8.00", "16.00", "B"),
    _p("TOY-003", "Yapboz 500 Parça", "toys", "oyuncak",
       "85.00", "149.00", "C"),
    _p("TOY-004", "Oyuncak Araba", "toys", "oyuncak",
       "45.00", "79.00", "B"),
    _p("TOY-005", "Peluş Ayı", "toys", "oyuncak", "120.00", "219.00", "C"),
    _p("TOY-006", "Hediye Paketi Kağıdı", "toys", "oyuncak",
       "6.00", "14.00", "B"),
    _p("TOY-007", "Doğum Günü Mumu", "toys", "oyuncak",
       "7.00", "15.00", "C"),
    # Bought in bulk before New Year, then worthless (see scenarios).
    _p("TOY-008", "Yılbaşı Süsü Seti", "toys", "oyuncak",
       "70.00", "129.00", "B", fade_from=date(2026, 1, 3)),
    # A fad that ends.
    _p("TOY-009", "Stres Çarkı", "toys", "oyuncak",
       "30.00", "59.00", "B", fade_from=date(2025, 12, 1)),
    _p("TOY-010", "Sabun Köpüğü", "toys", "oyuncak", "15.00", "29.00", "C"),

    # --- Telefon Aksesuarı ----------------------------------------
    _p("PHN-001", "USB-C Şarj Kablosu", "phone", "tekno",
       "45.00", "99.00", "B"),
    _p("PHN-002", "Şarj Adaptörü 20W", "phone", "tekno",
       "110.00", "219.00", "C"),
    _p("PHN-003", "Kablolu Kulaklık", "phone", "tekno",
       "80.00", "159.00", "C"),
    _p("PHN-004", "Telefon Kılıfı", "phone", "tekno",
       "50.00", "119.00", "C"),
    _p("PHN-005", "Ekran Koruyucu", "phone", "tekno",
       "25.00", "69.00", "C"),
    _p("PHN-006", "Powerbank 10000mAh", "phone", "tekno",
       "320.00", "549.00", "C"),
    _p("PHN-007", "Araç Şarj Cihazı", "phone", "tekno",
       "90.00", "179.00", "C"),
    _p("PHN-008", "Bluetooth Kulaklık", "phone", "tekno",
       "380.00", "649.00", "C", launch=date(2026, 3, 1)),
    _p("PHN-009", "Selfie Çubuğu", "phone", "tekno",
       "70.00", "139.00", "D"),
    _p("PHN-010", "Micro USB Kablo", "phone", "tekno",
       "30.00", "69.00", "D"),
)

# ---------------------------------------------------------------------
# Supplier cost changes (general inflation, staggered by supplier)
# ---------------------------------------------------------------------

COST_CHANGES = (
    CostChange("icecek", date(2025, 11, 3), 0.05),
    CostChange("icecek", date(2026, 3, 2), 0.06),
    CostChange("icecek", date(2026, 7, 6), 0.04),
    CostChange("gida", date(2025, 10, 6), 0.04),
    CostChange("gida", date(2026, 2, 2), 0.07),
    CostChange("gida", date(2026, 6, 1), 0.05),
    CostChange("kirtasiye", date(2026, 1, 5), 0.08),
    CostChange("kirtasiye", date(2026, 8, 3), 0.06),
    CostChange("temizlik", date(2025, 12, 1), 0.05),
    CostChange("temizlik", date(2026, 5, 4), 0.06),
    CostChange("oyuncak", date(2026, 2, 16), 0.07),
    CostChange("oyuncak", date(2026, 9, 7), 0.05),
    CostChange("tekno", date(2026, 1, 19), 0.08),
    CostChange("tekno", date(2026, 7, 20), 0.03),
)

# ---------------------------------------------------------------------
# Special days. Holiday dates are approximations.
# ---------------------------------------------------------------------

_FESTIVE = ("beverages", "snacks", "toys")

SPECIAL_DAYS = (
    SpecialDay(date(2025, 10, 29), 0.70, "Cumhuriyet Bayramı"),
    SpecialDay(date(2025, 12, 29), 1.40, "Yılbaşı alışverişi", _FESTIVE),
    SpecialDay(date(2025, 12, 30), 1.60, "Yılbaşı alışverişi", _FESTIVE),
    SpecialDay(date(2025, 12, 31), 1.80, "Yılbaşı alışverişi", _FESTIVE),
    SpecialDay(date(2026, 1, 1), 0.50, "Yılbaşı tatili"),
    SpecialDay(date(2026, 3, 18), 1.30, "Bayram öncesi", _FESTIVE),
    SpecialDay(date(2026, 3, 19), 1.40, "Bayram öncesi (arife)", _FESTIVE),
    SpecialDay(date(2026, 3, 20), 0.60, "Ramazan Bayramı"),
    SpecialDay(date(2026, 3, 21), 0.60, "Ramazan Bayramı"),
    SpecialDay(date(2026, 3, 22), 0.60, "Ramazan Bayramı"),
    SpecialDay(date(2026, 4, 23), 1.50, "23 Nisan Çocuk Bayramı", ("toys",)),
    SpecialDay(date(2026, 5, 1), 0.70, "1 Mayıs"),
    SpecialDay(date(2026, 5, 25), 1.30, "Bayram öncesi", _FESTIVE),
    SpecialDay(date(2026, 5, 26), 1.40, "Bayram öncesi (arife)", _FESTIVE),
    SpecialDay(date(2026, 5, 27), 0.60, "Kurban Bayramı"),
    SpecialDay(date(2026, 5, 28), 0.60, "Kurban Bayramı"),
    SpecialDay(date(2026, 5, 29), 0.60, "Kurban Bayramı"),
    SpecialDay(date(2026, 5, 30), 0.60, "Kurban Bayramı"),
    SpecialDay(date(2026, 8, 30), 0.70, "Zafer Bayramı"),
    SpecialDay(date(2026, 10, 29), 0.70, "Cumhuriyet Bayramı"),
)

# ---------------------------------------------------------------------
# Scripted exceptional scenarios
# ---------------------------------------------------------------------

SUPPLIER_DELAYS = (
    SupplierDelay(
        "temizlik",
        date(2026, 1, 5),
        date(2026, 1, 25),
        18,
        "Temizlik tedarikçisinde üç haftalık teslimat aksaması",
    ),
)

BULK_PURCHASES = (
    BulkPurchase(
        "TOY-008",
        date(2025, 11, 20),
        300,
        8.0,
        "Yılbaşı öncesi toplu alım (kampanya indirimi)",
    ),
)

DEMAND_SPIKES = (
    DemandSpike(
        "TOY-010",
        date(2026, 5, 10),
        date(2026, 5, 19),
        6.0,
        "Sosyal medyada popüler olan ürün",
    ),
)


def default_config(
    *,
    seed: int = DEFAULT_SEED,
    start: date = DEFAULT_START,
    end: date = DEFAULT_END,
) -> SimulationConfig:
    return SimulationConfig(
        seed=seed,
        start=start,
        end=end,
        suppliers=SUPPLIERS,
        categories=CATEGORIES,
        products=PRODUCTS,
        cost_changes=COST_CHANGES,
        special_days=SPECIAL_DAYS,
        supplier_delays=SUPPLIER_DELAYS,
        bulk_purchases=BULK_PURCHASES,
        demand_spikes=DEMAND_SPIKES,
    )
