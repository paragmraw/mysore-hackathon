#!/bin/sh
set -eu
if [ "${FRESH_DB:-0}" = "1" ]; then
  echo "[entrypoint] FRESH_DB=1 -> removing existing database..."
  rm -f "${DJANGO_DB_PATH:-db.sqlite3}"
fi

echo "[entrypoint] applying database migrations..."
python manage.py migrate --noinput
echo "[entrypoint] hydrating database from seed data (skipped if not empty)..."
python manage.py hydrate
python manage.py ensure_superuser
exec "$@"
