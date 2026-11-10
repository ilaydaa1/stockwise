# StockWise

An inventory management and analytics application for small retailers. It records products, purchases, sales and returns with full cost tracking, and ships with a realistic synthetic dataset for analysis. The interface is in Turkish.

The project's aim is to help a shop owner avoid two opposite losses: running out of products that sell, and tying up cash in products that do not.

## Features

- **Accounts** — registration and login with server-side sessions (HTTP-only cookie, hashed session tokens, argon2 password hashing, CSRF protection, rate-limited auth endpoints).
- **Business onboarding** — each user owns one business with its own currency and timezone. All data is scoped to that business.
- **Products** — create, edit, and soft-delete products with SKU, purchase price, sale price, and a minimum stock level. Products can be given a category and a supplier with a lead time.
- **Stock ledger** — every change to stock, including a product's opening stock, is a movement that records the level before and after and the unit cost it was valued at.
- **Inventory costing** — moving weighted average cost. Each sale line freezes the cost at the time of sale, so later purchases never change past profit. See [docs/costing.md](docs/costing.md).
- **Sales** — multi-item sales that are all-or-nothing: product rows are locked, stock is checked for every item, and prices are snapshotted onto the sale.
- **Returns** — full or partial returns linked to the original sale line, restoring stock and recording the refund, so net sales can be calculated.
- **Data integrity** — database constraints reject invalid rows, and a set of cross-record checks reconciles the ledger, sales and returns.
- **Synthetic dataset** — fifteen months of simulated history for one fictional shop, reproducible from a fixed seed. See [docs/dataset.md](docs/dataset.md).
- **Dashboard and analytics** — revenue, gross profit, margin, daily performance, critical stock, and per-product metrics (average daily sales, stock coverage, sales trend).

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | React 19, TypeScript, Vite, Tailwind CSS, React Router |
| Backend | Python 3.11+, FastAPI, SQLAlchemy 2, Pydantic 2, Alembic |
| Database | PostgreSQL 16 (via Docker Compose) |
| Tests | Pytest |

## Project structure

```
backend/
  alembic/                 database migrations
  stockwise/app/
    api/                   one folder per feature: router + schemas
    core/                  settings, auth dependencies, security, rate limiter
    db/                    engine and session
    models/                SQLAlchemy models
    services/              business logic: inventory, sales, returns,
                           integrity checks, product analysis
  stockwise/datagen/       synthetic data generator
  tests/                   API and unit tests
frontend/
  src/
    pages/                 one file per screen
    components/            layout and shared components
    contexts/              auth and business state
    lib/api.ts             typed API client
data/synthetic/            generated dataset (CSV) and its manifest
docs/                      dataset and costing documentation
compose.yaml               local PostgreSQL
```

## Getting started

Requirements: Docker, Python 3.11+, Node.js 20+.

### 1. Database

```bash
docker compose up -d
```

This starts PostgreSQL on port 5432 with the user, password, and database name `stockwise` / `stockwise_local_password` / `stockwise`. Override them with `POSTGRES_USER`, `POSTGRES_PASSWORD`, and `POSTGRES_DB`.

### 2. Backend

Run these from the `backend` folder.

```bash
python -m venv .venv
```

Activate the virtual environment (`.venv\Scripts\activate` on Windows, `source .venv/bin/activate` on macOS and Linux), then:

```bash
pip install -e ".[dev]"
```

Copy `.env.example` to `.env` and adjust the values if needed, then apply the migrations and start the API:

```bash
alembic upgrade head
```

```bash
uvicorn stockwise.app.main:app --reload
```

The API runs at http://localhost:8000, with interactive documentation at http://localhost:8000/docs.

### 3. Frontend

Run these from the `frontend` folder.

```bash
npm install
```

```bash
npm run dev
```

The app runs at http://localhost:5173. To point it at a different API, copy `.env.example` to `.env` and set `VITE_API_BASE_URL`.

## Synthetic dataset

The repository includes a generated dataset in [`data/synthetic/`](data/synthetic/): about 23,600 sales over fifteen months for a fictional shop with 80 products. **It is entirely artificial.**

To load it into your own database and rewrite the files, run this from the `backend` folder after applying the migrations:

```bash
python -m stockwise.datagen generate --reset
```

The data goes into a separate demo account and does not touch other accounts. To sign in as that account, set the `DEMO_USER_PASSWORD` environment variable before generating; without it the demo account has login disabled.

The assumptions, file layout and scripted scenarios are described in [docs/dataset.md](docs/dataset.md).

## Tests

From the `backend` folder:

```bash
pytest
```

The tests use an in-memory SQLite database, so they do not need PostgreSQL to be running. This also means PostgreSQL-specific behaviour, such as row locking during sales, is not covered by the suite.

## API overview

All routes are under `/api`.

| Route | Purpose |
|---|---|
| `GET /health`, `GET /ready` | Liveness and database readiness |
| `POST /auth/register`, `POST /auth/login`, `POST /auth/logout`, `GET /auth/me` | Authentication |
| `POST /businesses`, `GET /businesses/me` | Business onboarding |
| `GET/POST /categories` | Product categories |
| `GET/POST /suppliers`, `PATCH /suppliers/{id}` | Suppliers and lead times |
| `GET/POST /products`, `GET/PATCH/DELETE /products/{id}` | Product management |
| `GET/POST /stock-movements` | Manual stock changes and history |
| `POST /sales` | Create a sale |
| `GET/POST /sales/{id}/returns` | Return lines of a sale |
| `GET /dashboard/summary` | Last 15 days at a glance |
| `GET /analytics/summary`, `GET /analytics/products` | Sales and product analytics |

State-changing requests need the `x-csrf-token` header, set to the value of the `sw_csrf` cookie.

## Known limitations

- Daily figures are grouped by UTC date, not the business timezone.
- List endpoints are not paginated.
- Dashboard and analytics figures are gross: they do not yet subtract returns.
- Categories, suppliers and returns are available through the API only; the interface has no screens for them yet.
- The automated tests run on SQLite, so PostgreSQL row locking is not exercised by them.
- The backend and frontend are not containerised; Docker Compose only provides the database.
- There are no frontend tests and no CI pipeline yet.
