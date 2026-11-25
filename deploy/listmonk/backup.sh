#!/bin/sh
# Saves a copy of the subscriber list and settings to backups/ (keeps the last 30).
# Run by hand, or every night from cron: 30 2 * * * cd ~/chai-list && ./backup.sh
set -e
cd "$(dirname "$0")"
mkdir -p backups
docker compose exec -T listmonk-db pg_dump -U listmonk listmonk | gzip > "backups/listmonk-$(date +%F).sql.gz"
ls -1t backups/listmonk-*.sql.gz | tail -n +31 | xargs -r rm --
echo "Backup saved: backups/listmonk-$(date +%F).sql.gz"
