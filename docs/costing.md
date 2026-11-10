# Inventory costing: moving weighted average

StockWise values inventory and calculates cost of goods sold (COGS) with the **moving weighted average cost** method. This document describes the rules, the reasons for them, and their limits.

The implementation is in [`services/inventory.py`](../backend/stockwise/app/services/inventory.py). The tests are in [`tests/test_costing.py`](../backend/tests/test_costing.py).

## Why this method

A shop buys the same product many times at different prices. When a unit is sold, the system has to decide what that unit cost.

| Method | Idea | Why not here |
|---|---|---|
| Latest cost | Every unit costs whatever was paid most recently | Profit on old stock is misstated the moment a new price arrives |
| FIFO | Track each purchase batch and sell the oldest first | Accurate, but needs batch tracking for every unit |
| **Moving weighted average** | All units on hand share one blended cost | Good accuracy with one number per product |

The weighted average is the common choice for small retailers selling interchangeable units, and it gives stable margins when costs drift.

## The fields involved

| Field | Meaning |
|---|---|
| `products.average_cost` | Blended cost of the units currently in stock. Four decimals. Maintained by the system only. |
| `products.purchase_price` | The latest price paid to the supplier. Used as the default cost for the next stock-in. |
| `stock_movements.unit_cost` | The cost per unit that one movement was valued at. Four decimals. |
| `sale_items.unit_purchase_price` | The average cost at the moment of sale, frozen on the sale line. Two decimals. |

## Rules by movement type

When units arrive with their own cost, the average is recalculated:

```
new average = (stock before × average before + quantity × unit cost)
              ÷ (stock before + quantity)
```

| Movement | Stock | Cost used | Effect on the average |
|---|---|---|---|
| `OPENING` | up | The product's purchase price | Recalculated |
| `IN` | up | The price paid (`unit_cost`), or the current purchase price if omitted | Recalculated; `purchase_price` is updated to this cost |
| `RETURN` | up | The cost the units were originally sold at | Recalculated |
| `ADJUSTMENT_IN` | up | The current average | Unchanged |
| `SALE` | down | The current average | Unchanged |
| `OUT` | down | The current average | Unchanged |
| `ADJUSTMENT_OUT` | down | The current average | Unchanged |

Units leaving stock never change the average: removing units at the average cost leaves the average of what remains the same.

## Worked example

| Step | Event | Stock | Average cost | Note |
|---|---|---|---|---|
| 1 | Product created with 10 units at 10.00 | 10 | 10.0000 | `OPENING` |
| 2 | Sell 6 | 4 | 10.0000 | COGS = 6 × 10.00 = 60.00 |
| 3 | Receive 4 at 20.00 | 8 | 15.0000 | (4 × 10 + 4 × 20) ÷ 8 |
| 4 | Sell 2 | 6 | 15.0000 | COGS = 2 × 15.00 = 30.00 |
| 5 | Customer returns 2 units from step 2 | 8 | 13.7500 | (6 × 15 + 2 × 10) ÷ 8 |

The sale in step 2 keeps its cost of 10.00 per unit forever. The purchase in step 3 does not change it.

## Historical profit never changes

A sale line stores `unit_purchase_price`, `cost` and `gross_profit` at the time of sale. Nothing recalculates them later. Buying stock at a new price changes `products.average_cost`, which only affects sales made afterwards.

## Returns

A return points at the sale line it reverses and stores two amounts, both taken from the prices frozen on that line:

- `refund_amount` = returned quantity × original unit sale price
- `cost_amount` = returned quantity × original unit cost

The original sale is not modified. This gives:

- net sales = gross sales − refunds
- net COGS = gross COGS − returned cost

Returned units re-enter stock at their original cost, which reverses the COGS for exactly those units.

## Assumptions and limits

- **Opening stock** is valued at the purchase price entered when the product is created.
- **Stock that existed before cost tracking** was valued at the purchase price known at migration time. This is an estimate.
- **Rounding.** The average is kept to four decimals; the cost on a sale line is rounded to two. The total of all sale costs can therefore differ from stock value changes by a fraction of a cent per line.
- **Restocking from zero.** When stock is zero, the next costed arrival sets the average to its own cost.
- **Manual adjustments** are valued at the current average. A stock count surplus does not bring a new cost with it.
- **Editing `purchase_price`** on a product changes the default for the next stock-in only. It does not revalue stock on hand.
- **Returned units are assumed resaleable.** Damaged returns are not written off automatically; record an `ADJUSTMENT_OUT` for them.
- **No landed costs.** Freight, duties and discounts received after the purchase are not allocated to units.
