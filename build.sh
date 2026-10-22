#!/usr/bin/env bash
set -o errexit

export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-config.settings.production}"

if [[ -z "${DATABASE_URL:-}" ]]; then
    echo "DATABASE_URL must be configured before running the production build." >&2
    exit 1
fi

case "${DATABASE_URL}" in
    postgres://*|postgresql://*) ;;
    *)
        echo "DATABASE_URL must point to a PostgreSQL database for the production build." >&2
        exit 1
        ;;
esac

pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate --noinput
python manage.py ensure_superuser
if [[ "${SEED_ON_DEPLOY:-false}" == "true" ]]; then
    if [[ -z "${SEED_DEMO_PASSWORD:-}" ]]; then
        echo "SEED_DEMO_PASSWORD must be configured before SEED_ON_DEPLOY is enabled." >&2
        exit 1
    fi
    python manage.py seed_production --confirm
    python manage.py seed_parul_data
    python manage.py seed_delivery_data
fi
python manage.py seed_product_images
python manage.py lockdown_db
