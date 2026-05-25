#!/bin/sh
set -e
if [ -z "$1" ]; then
  echo "Usage: restore_postgres.sh <backup.sql.gz>"
  exit 1
fi
gunzip -c "$1" | psql "$DATABASE_URL"
echo "Restore completed from $1"
