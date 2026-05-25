#!/bin/sh
set -e
TIMESTAMP=$(date -u +"%Y%m%dT%H%M%SZ")
BACKUP_DIR="${BACKUP_DIR:-./backups}"
mkdir -p "$BACKUP_DIR"
FILE="$BACKUP_DIR/djablinest_${TIMESTAMP}.sql.gz"
pg_dump "$DATABASE_URL" | gzip > "$FILE"
echo "Backup saved: $FILE"
