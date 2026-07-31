#!/usr/bin/env bash
# QRdasturxon zaxira nusxasi: baza + yuklangan rasmlar.
#
# Ishlatish (loyiha katalogidan):
#   ./scripts/backup.sh [qayerga-saqlash]
#
# Har kuni tunda ishlashi uchun crontab'ga qo'shing:
#   0 3 * * * cd /srv/qrdasturxon && ./scripts/backup.sh >> /var/log/qrdasturxon-backup.log 2>&1

set -euo pipefail

DEST="${1:-./backups}"
STAMP="$(date +%Y%m%d-%H%M%S)"
KEEP_DAYS="${KEEP_DAYS:-30}"

mkdir -p "$DEST"

echo "[$(date +%H:%M:%S)] Baza saqlanmoqda..."
docker compose exec -T db pg_dump \
  --username "${POSTGRES_USER:-qrdasturxon}" \
  --dbname "${POSTGRES_DB:-qrdasturxon}" \
  | gzip > "$DEST/db-$STAMP.sql.gz"

echo "[$(date +%H:%M:%S)] Rasmlar saqlanmoqda..."
docker compose run --rm --no-deps --entrypoint sh -v "$(cd "$DEST" && pwd):/backup" app \
  -c "tar czf /backup/media-$STAMP.tar.gz -C /app media"

# Bo'sh yoki juda kichik fayl — zaxira ishlamaganini bildiradi
for file in "$DEST/db-$STAMP.sql.gz" "$DEST/media-$STAMP.tar.gz"; do
  if [ ! -s "$file" ]; then
    echo "XATO: $file bo'sh chiqdi — zaxira muvaffaqiyatsiz" >&2
    exit 1
  fi
done

echo "[$(date +%H:%M:%S)] Eski nusxalar tozalanmoqda ($KEEP_DAYS kundan eski)..."
find "$DEST" -name 'db-*.sql.gz' -mtime "+$KEEP_DAYS" -delete
find "$DEST" -name 'media-*.tar.gz' -mtime "+$KEEP_DAYS" -delete

echo "[$(date +%H:%M:%S)] Tayyor:"
ls -lh "$DEST/db-$STAMP.sql.gz" "$DEST/media-$STAMP.tar.gz"
