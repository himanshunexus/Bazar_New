# BAZAR

BAZAR is a Django 5.1 hyperlocal marketplace for India. Customers discover nearby shops, add products from multiple shops to one session cart, and place Cash on Delivery orders. Checkout splits the cart into one order per shop.

## Local Setup

```bash
cp .env.example .env
docker compose up -d db
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

Run tests:

```bash
pytest
```

Run the ML service locally:

```bash
docker compose up --build ml
```

Free-tier Render services can sleep. The first ML call may time out; the Django app falls back to trending active products and opens a 30-second circuit breaker.

## Required Environment Variables

- `SECRET_KEY`
- `DEBUG`
- `ALLOWED_HOSTS`
- `CSRF_TRUSTED_ORIGINS`
- `DATABASE_URL`
- `DB_CONN_MAX_AGE`
- `DB_SSL_REQUIRE`
- `DISABLE_SERVER_SIDE_CURSORS`
- `CLOUDINARY_CLOUD_NAME`
- `CLOUDINARY_API_KEY`
- `CLOUDINARY_API_SECRET`
- `ML_SERVICE_URL`
- `DEFAULT_LAT`
- `DEFAULT_LNG`
- `DEFAULT_RADIUS_KM`

## Deployment

Render uses `render.yaml`.

- `bazar-web`: native Python service, build command `./build.sh`, start command `gunicorn config.wsgi:application`, health check `/healthz`.
- `bazar-ml`: Docker service with `ml_service/Dockerfile`, health check `/health`.

For Supabase, use the pooler connection string. If the pooler is transaction mode, set `DISABLE_SERVER_SIDE_CURSORS=True`. Run `python manage.py lockdown_db` after migrations.
The production build requires `DATABASE_URL` to be configured as a PostgreSQL URL; it will fail rather than migrate a local SQLite database.

Payments are COD only. The codebase intentionally contains no online payment gateway integrations.
