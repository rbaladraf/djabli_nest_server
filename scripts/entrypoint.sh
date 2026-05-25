#!/bin/sh
set -e

echo "Running database migrations..."
alembic upgrade head

if [ -n "$INITIAL_SUPERADMIN_USERNAME" ]; then
  python -m app.cli create-superadmin || true
fi

echo "Starting API server..."
exec gunicorn app.main:app \
  --workers 2 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 120 \
  --access-logfile - \
  --error-logfile -
