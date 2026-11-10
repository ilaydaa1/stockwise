# The synthetic dataset

> **All of this data is artificial.** It was produced by a simulation. It does not describe any real business, person, supplier or transaction. Supplier and product names are invented.

The dataset gives StockWise about fifteen months of history to analyse: sales, purchases, returns, stock counts and price changes for one fictional shop. It lives in [`data/synthetic/`](../data/synthetic/) and is produced by the generator in [`backend/stockwise/datagen/`](../backend/stockwise/datagen/).

## The shop

A small general retail shop in Istanbul, open every day from 09:00 to 21:00. It sells about 80 products in 8 categories, bought from 6 suppliers. Prices are in Turkish lira. Perishable goods are left out so that expiry dates do not need modelling.

| | |
|---|---|
| Period | 1 August 2025 to 31 October 2026 (457 days) |
| Products | 80 (75 from day one, 5 launched later) |
| Categories | 8 |
| Suppliers | 6, with lead times of 2, 3, 5, 7, 14 and 21 days |
| Sales | about 23,600, with about 41,500 lines |
| Random seed | 42 |

August to October appears twice, so those months can be compared year over year.

## Files

All timestamps are UTC in ISO 8601 format. The shop's local time is Europe/Istanbul (UTC+3).

| File | One row per | Notes |
|---|---|---|
| `categories.csv` | category | |
| `suppliers.csv` | supplier | `lead_time_days` is the nominal lead time |
| `products.csv` | product | State at the end of the period: current prices, average cost and stock |
| `sales.csv` | sale (basket) | Totals for the whole basket |
| `sale_items.csv` | sale line | Unit price and unit cost frozen at the time of sale |
| `sale_returns.csv` | returned line | Links to `sale_items.id`; refund and cost amounts |
| `stock_movements.csv` | stock change | The full ledger, with the level before and after each change |
| `manifest.json` | — | Seed, period, row counts and the list of scripted scenarios |
| `ground_truth/daily_demand.csv` | product and day | True demand, including demand lost to stockouts |
| `ground_truth/purchasing_policy.csv` | product | The parameters the simulation used for each product |

### Keys

```
categories.id  ←  products.category_id
suppliers.id   ←  products.supplier_id
products.id    ←  sale_items.product_id, stock_movements.product_id
sales.id       ←  sale_items.sale_id, stock_movements.sale_id
sale_items.id  ←  sale_returns.sale_item_id
sale_returns.id ← stock_movements.sale_return_id
```

### Movement types

| Type | Direction | Meaning |
|---|---|---|
| `OPENING` | in | Stock a product started with |
| `IN` | in | Delivery from a supplier; `unit_cost` is the price paid |
| `SALE` | out | Units sold; linked to a sale |
| `RETURN` | in | Units returned by a customer; linked to a return |
| `ADJUSTMENT_OUT` | out | Shrinkage found in a stock count |
| `ADJUSTMENT_IN` | in | Surplus found in a stock count |

### The ground truth folder

A real shop knows what it sold, not what it could have sold. When a product is out of stock, the customers who wanted it leave no record.

Because this data is simulated, the true demand is known. It is kept out of the database and out of the main files, in `ground_truth/`, so that an analysis can first estimate lost sales from the observable data and then check the estimate against the truth. Treat this folder as an answer key, not as input.

## How the data is generated

For each day, in this order:

1. Supplier cost changes take effect. Sale prices follow 21 days later.
2. New products are introduced.
3. Deliveries arrive before the shop opens.
4. Customers arrive. Each product's demand for the day is drawn at random. Sales are capped by the stock on hand; the rest is lost.
5. Earlier sales are returned.
6. On the last day of each month, a stock count finds small differences.
7. In the evening the owner reorders.

### Demand

Each product has a base level of daily demand. The expected demand on a given day is that base level multiplied by:

| Factor | Source |
|---|---|
| Season | A monthly multiplier per category, blended smoothly between months |
| Day of week | A multiplier per category |
| Trend | Each product drifts between −15% and +20% per year |
| Special days | Public holidays and the days before them |
| Scenarios | Demand spikes and fading products (below) |

The actual number of units demanded is a Poisson draw around that expectation. This is a simple, explainable model; it contains no machine learning.

Seasonal patterns by category:

| Category | Pattern |
|---|---|
| Beverages | Strong summer peak; busier at weekends |
| Snacks | Nearly flat; busier at weekends |
| Stationery | Back-to-school peak in September, smaller peak in February; quiet at weekends |
| Household cleaning | Mild spring bump |
| Personal care | Flat |
| Winter goods | Sells from October to February, almost nothing in summer |
| Toys and gifts | Large December peak; much busier at weekends |
| Phone accessories | Flat, slow-moving, highest return rate |

### Velocity classes

| Class | Share of products | Base demand per day |
|---|---|---|
| A — fast movers | about 14% | 2.5 to 6 units |
| B — regular | about 44% | 0.8 to 2.2 units |
| C — slow movers | about 35% | 0.15 to 0.6 units |
| D — barely sell | about 8% | the owner expected 0.5 to 1.5; real demand is 6% of that |

### The owner's purchasing policy

This is the most important assumption, because it creates the problems the project sets out to solve.

The owner uses a fixed rule for each product, worked out once from the sales expected on an average day:

- **Minimum stock** covers the supplier's lead time plus two days of average sales.
- **Order quantity** covers fourteen days of average sales, rounded up to packs of six.
- Every evening except Sunday, any product at or below its minimum is reordered.

The rule never adapts to season, trend or actual sales. As a result:

- seasonal products **run out** at their peak, especially those with long lead times;
- products whose demand fades or never appears are left as **dead stock**.

### Costs and prices

Each supplier raises its prices two or three times during the period, by 3% to 8%. The shop's sale prices follow three weeks later, rounded to the nearest 0.50. Margins are squeezed in between.

Cost of goods sold uses the moving weighted average method described in [costing.md](costing.md).

### Returns and stock counts

- A sold line is later returned with a probability set per category, from 0.5% (beverages) to 6% (phone accessories), within 1 to 10 days.
- At each month end, a product with stock has a 12% chance of showing a loss of 1 to 3 units and a 2% chance of a surplus of 1 or 2.

## Scripted scenarios

These events are placed deliberately, so that an analysis has known things to find. The exact dates are in `manifest.json`.

| Scenario | What happens |
|---|---|
| Supplier disruption | Orders placed with the cleaning supplier in January 2026 arrive 18 days late, causing stockouts across household cleaning and personal care |
| Bulk over-purchase | 300 New Year decoration sets are bought at a discount in November 2025; demand ends in early January and most are never sold |
| Demand spike | One toy sells at six times its usual rate for ten days in May 2026 |
| Dated product | A 2025 diary stops selling from October 2025 |
| Ended fad | One toy's demand collapses from December 2025 |
| Product launches | Five products are introduced during the period |
| Cost increases | Fourteen supplier price rises, each followed by a shelf price change |
| Products that barely sell | Six products the owner misjudged from the start |

## Consistency guarantees

The history is loaded through the same code paths as live transactions, so it obeys the same rules:

- A sale can never exceed the stock on hand. There are no backorders.
- Every stock change has a movement recording the level before and after.
- Each movement starts from the level the previous one ended on.
- A product's stock equals the level after its last movement.
- Returned quantity never exceeds sold quantity.
- Sale totals equal the sum of their lines.
- Nothing is dated before the thing it depends on.

The generator checks all of these after loading and refuses to export if any check fails.

## Regenerating the dataset

From the `backend` folder:

```bash
python -m stockwise.datagen generate --reset
```

This simulates the history, loads it into a dedicated demo account in the application database, validates it and rewrites the CSV files. The same seed always produces byte-identical files.

To generate without PostgreSQL, into a throwaway SQLite file:

```bash
python -m stockwise.datagen generate --database-url sqlite:///demo.db --create-schema
```

Useful options: `--seed`, `--start`, `--end`, `--out` and `--no-export`. To change the assumptions themselves, edit [`datagen/config.py`](../backend/stockwise/datagen/config.py), where every one of them is defined.

The demo account (`demo@stockwise.example`) cannot be logged into unless the `DEMO_USER_PASSWORD` environment variable is set when generating.

## Limits of this dataset

- **It is synthetic.** Patterns are cleaner than in real data, and findings partly recover what was put in. The value is in the method, which can be checked against known answers.
- **One shop, one owner, one fixed policy.** There is no learning, no promotions and no competitors.
- **No price elasticity.** Price changes do not affect demand.
- **No customers.** Sales are anonymous baskets; there is no customer or loyalty data.
- **Baskets are random.** Products are grouped into baskets by chance, so there are no real cross-selling patterns to discover.
- **Lead times are simple.** Only the goods receipt is recorded, not the order date, so actual versus promised lead time cannot be analysed.
- **Holiday dates are approximate.**
- **Returned goods are always resaleable.**
