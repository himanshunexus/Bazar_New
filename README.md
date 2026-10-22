# BAZAR

BAZAR is a Django marketplace for discovering neighbourhood shops and ordering local products for cash on delivery. It includes customer, shop-owner/staff, rider, and administrator workflows, a location-aware shop map, order tracking, product photos, and an optional ML recommendation service.

## Features

- Shop and product discovery scoped to the customer’s delivery area, with a 5 km checkout limit.
- Cart checkout, shop order management, rider assignment and status updates, and customer order tracking.
- Orders without a rider are cancelled after five minutes when the cancellation command runs; see **Operations**.
- Role-based customer, shop, staff, rider, and admin access.
- Optional recommendation API with a trending-products fallback when the model service is unavailable.
- PostgreSQL for production, Cloudinary for product images, and a separate FastAPI recommendation service.

## Run locally

Requirements: Python 3.11+ and PostgreSQL (or SQLite for a lightweight local run).

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Set a local `SECRET_KEY` and `DATABASE_URL` in `.env`. For PostgreSQL, create the database first. For SQLite, remove `DATABASE_URL` so Django uses `db.sqlite3`.

```bash
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

Open <http://127.0.0.1:8000/>. Run the test suite with:

```bash
pytest
```

## Services

| Service | Entrypoint | Purpose |
| --- | --- | --- |
| Django web | `config.wsgi:application` | Marketplace, accounts, shops, products, cart, orders, and admin |
| Recommendation API | `ml_service/app.py` | FastAPI endpoint serving product recommendations |

Run the model service locally with `docker compose up --build ml`. Set `ML_SERVICE_URL` to its `/predict` endpoint. If it is unavailable, the web app serves trending products instead.

## Configuration

Copy `.env.example` and set values for your environment. Production requires `SECRET_KEY`, `DATABASE_URL`, `ALLOWED_HOSTS`, and `CSRF_TRUSTED_ORIGINS`. Configure `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, and `CLOUDINARY_API_SECRET` to enable managed product-photo uploads. `DEFAULT_LAT`, `DEFAULT_LNG`, and `DEFAULT_RADIUS_KM` set the default service area; the default centre is near Parul University and the radius is 5 km.

For Supabase PostgreSQL, use its pooler URL and set `DB_SSL_REQUIRE=True`. Set `DISABLE_SERVER_SIDE_CURSORS=True` when using transaction pooling. Do not commit `.env` or production credentials.

## Deployment

Render configuration is in `render.yaml`. The Django service runs `./build.sh`, starts Gunicorn, and exposes `/healthz`. The recommendation service builds from `ml_service/Dockerfile` and exposes `/health`.

The web build installs dependencies, collects static files, applies migrations, ensures the configured superuser exists, seeds product images, and applies the database lockdown command. Demo account and Parul-area sample data are only seeded when `SEED_ON_DEPLOY=true`; set `SEED_DEMO_PASSWORD` before enabling it. Configure `DJANGO_SUPERUSER_USERNAME`, `DJANGO_SUPERUSER_EMAIL`, and `DJANGO_SUPERUSER_PASSWORD` to create or update the admin account.

## Operations

Run pending unassigned-order cancellations with:

```bash
python manage.py cancel_unassigned_orders
```

Schedule this command to run once per minute in the hosting platform for automatic five-minute cancellation. The command is safe to run repeatedly.

Retrain recommendations after meaningful order-history changes:

```bash
python manage.py export_orders_for_ml orders.csv
cd ml_service
python train.py --csv ../orders.csv
```

Commit the updated `ml_service/model/model.pkl` and `ml_service/model/product_ids.pkl` with the corresponding code/data change. Payments currently support cash on delivery only.
