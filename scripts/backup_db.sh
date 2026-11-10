#!/usr/bin/env bash
# Backup do PostgreSQL (container db) com pg_dump.
# Uso:     bash scripts/backup_db.sh            -> gera src/backups/lavoura_AAAA-MM-DD_HHMM.sql.gz
# Restaurar: gunzip -c src/backups/<arquivo>.sql.gz | docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
set -euo pipefail

cd "$(dirname "$0")/../src"
if docker info >/dev/null 2>&1; then DOCKER="docker"; else DOCKER="sudo docker"; fi
mkdir -p backups
ARQUIVO="backups/lavoura_$(date +%F_%H%M).sql.gz"
$DOCKER compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner' | gzip > "$ARQUIVO"
echo "Backup gerado: src/$ARQUIVO ($(du -h "$ARQUIVO" | cut -f1))"
echo "Copie para fora da EC2 (ex.: aws s3 cp src/$ARQUIVO s3://<bucket>/) para não perder junto com a instância."
