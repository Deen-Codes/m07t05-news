#!/usr/bin/env bash
# wait for db, migrate, seed groups, run CMD

set -euo pipefail

DB_HOST="${DJANGO_DB_HOST:-db}"
DB_PORT="${DJANGO_DB_PORT:-3306}"

echo "[entrypoint] waiting for MariaDB at ${DB_HOST}:${DB_PORT}"
for attempt in $(seq 1 60); do
    if nc -z "${DB_HOST}" "${DB_PORT}"; then
        echo "[entrypoint] MariaDB is reachable"
        break
    fi
    echo "[entrypoint] attempt ${attempt}/60: not ready yet, sleeping 1s"
    sleep 1
done

echo "[entrypoint] applying migrations"
python manage.py migrate --noinput

echo "[entrypoint] seeding role groups"
python manage.py seed_groups

echo "[entrypoint] handing off to: $*"
exec "$@"
