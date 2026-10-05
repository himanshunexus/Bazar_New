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
    python manage.py seed_production --confirm
fi
python manage.py lockdown_db
