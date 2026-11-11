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
compose.yaml               database, migrations, backend and frontend
```

## Getting started

There are two ways to run StockWise. Docker is the quickest; the local setup is better while changing code.

### Option A: everything in Docker

Requirement: Docker Desktop. No Python or Node.js installation is needed.

Start the database, apply migrations, and start the backend and frontend:

```bash
docker compose up -d --build
```

Then open http://localhost:3000. The API documentation is at http://localhost:8000/docs.

| Task | Command |
|---|---|
| See what is running | `docker compose ps` |
| Follow the logs | `docker compose logs -f backend` |
| Stop, keeping containers | `docker compose stop` |
| Start again | `docker compose start` |
| Stop and remove containers (data is kept) | `docker compose down` |
| Rebuild after changing code | `docker compose up -d --build --force-recreate` |
| Open a database shell | `docker compose exec postgres psql -U stockwise -d stockwise` |

The database lives in a Docker volume named `stockwise_stockwise_pgdata`, which survives all of the commands above.

> **Warning:** `docker compose down -v` deletes that volume and with it all data. Only use it when you want an empty database.

What happens on `up`:

1. `postgres` starts and waits until it accepts connections.
2. `migrate` applies any pending database migrations, then exits. Seeing it as "Exited (0)" is normal.
3. `backend` starts once the migrations have finished.
4. `frontend` serves the site and forwards requests under `/api` to the backend, so the browser only talks to one address.

To change ports or passwords, copy `.env.example` to `.env` in the project root and edit it.

#### Troubleshooting

| Symptom | Cause and fix |
|---|---|
| "port is already allocated" | Another program uses port 3000, 8000 or 5432. Set `FRONTEND_PORT`, `BACKEND_PORT` or `POSTGRES_PORT` in `.env`. A backend started by hand (Option B) also occupies port 8000; stop it first. |
| `migrate` shows "Exited (1)" | A migration failed. Read `docker compose logs migrate`. |
| Site loads but login says "Origin not allowed" | The site is being opened on a port the backend does not expect. Use the port set in `FRONTEND_PORT`. |
| Code changes do not appear | Images are built from the code at build time, and a rebuilt image is only used once its container is recreated. Run `docker compose up -d --build --force-recreate`. The database restarts for a few seconds; its data is kept. |

### Option B: local development

Requirements: Docker (for the database only), Python 3.11+, Node.js 20+.

#### 1. Database

```bash
docker compose up -d postgres
```

This starts only PostgreSQL, on port 5432.

#### 2. Backend

Run these from the `backend` folder.

```bash
python -m venv .venv
```

Activate the virtual environment (`.venv\Scripts\Activate.ps1` in PowerShell, `source .venv/bin/activate` on macOS and Linux), then:

```bash
pip install -r requirements-dev.txt
```

Apply the migrations and start the API:

```bash
alembic upgrade head
```

```bash
uvicorn stockwise.app.main:app --reload
```

The API runs at http://localhost:8000, with interactive documentation at http://localhost:8000/docs. Settings can be overridden by copying `backend/.env.example` to `backend/.env`.

#### 3. Frontend

Run these from the `frontend` folder.

```bash
npm install
```

```bash
npm run dev
```

The app runs at http://localhost:5173 and reloads as you edit.

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
| `GET/POST /stock-movements` | Manual stock changes; history is paged and searchable, with the total in the `X-Total-Count` header |
| `GET/POST /sales` | List sales (paginated) and create a sale |
| `GET/POST /sales/{id}/returns` | Return lines of a sale |
| `GET /dashboard/summary` | Last 15 days at a glance |
| `GET /analytics/summary`, `GET /analytics/products` | Sales and product analytics |

State-changing requests need the `x-csrf-token` header, set to the value of the `sw_csrf` cookie.

## Known limitations

- Daily figures are grouped by UTC date, not the business timezone.
- The product list is not paginated; it is loaded whole.
- Categories cannot be renamed or deleted, and suppliers cannot be deleted.
- The automated tests run on SQLite, so PostgreSQL row locking is not exercised by them.
- The Docker setup is for local use: it has no HTTPS, and the rate limiter sees every request as coming from the web server container.
- There are no frontend tests and no CI pipeline yet.
