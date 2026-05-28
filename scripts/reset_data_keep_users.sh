#!/bin/sh
set -e

# Reset all tables except `users` and `alembic_version`.
# Requires docker compose and running postgres service.

docker compose exec -T postgres psql -U djabli -d djablinest < ./scripts/reset_data_keep_users.sql
echo "OK: data reset (kept users)."

