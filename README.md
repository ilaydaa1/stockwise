# StockWise

A stock management application for small businesses: products, stock movements, sales, and sales analytics. The interface is in Turkish.

## Features

- **Accounts** — registration and login with server-side sessions (HTTP-only cookie, hashed session tokens, argon2 password hashing, CSRF protection, rate-limited auth endpoints).
- **Business onboarding** — each user owns one business with its own currency and timezone. All data is scoped to that business.
- **Products** — create, edit, and soft-delete products with SKU, purchase price, sale price, and a minimum stock level.
- **Stock movements** — manual stock in, out, and adjustments. Every change records the stock level before and after.
- **Sales** — multi-item sales that are all-or-nothing: product rows are locked, stock is checked for every item, and prices are snapshotted onto the sale.
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
    services/              business logic (product analysis)
  tests/                   API and unit tests
frontend/
  src/
    pages/                 one file per screen
    components/            layout and shared components
    contexts/              auth and business state
    lib/api.ts             typed API client
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
| `GET/POST /products`, `GET/PATCH/DELETE /products/{id}` | Product management |
| `GET/POST /stock-movements` | Manual stock changes and history |
| `POST /sales` | Create a sale |
| `GET /dashboard/summary` | Last 15 days at a glance |
| `GET /analytics/summary`, `GET /analytics/products` | Sales and product analytics |

State-changing requests need the `x-csrf-token` header, set to the value of the `sw_csrf` cookie.

## Known limitations

- Daily figures are grouped by UTC date, not the business timezone.
- List endpoints are not paginated.
- There is no sale refund or void.
- The backend and frontend are not containerised; Docker Compose only provides the database.
- There are no frontend tests and no CI pipeline yet.
