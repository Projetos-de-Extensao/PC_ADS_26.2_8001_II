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
# Envia para o bucket privado somente quando configurado e explicitamente habilitado.
BUCKET=$(sed -n 's/^RAIZES_S3_BUCKET=//p' .env | tail -1 | tr -d '\r')
ENVIAR_S3=$(sed -n 's/^RAIZES_BACKUP_S3_ENABLED=//p' .env | tail -1 | tr -d '\r')
if [ "${1:-}" = "--s3-once" ]; then ENVIAR_S3=1; fi
if [ "$ENVIAR_S3" = "1" ] && [ -n "$BUCKET" ]; then
  aws s3 cp "$ARQUIVO" "s3://$BUCKET/backups/postgres/$(basename "$ARQUIVO")" --sse AES256 --only-show-errors
  echo "Backup PostgreSQL enviado ao S3 privado."
  MEDIA="backups/media_$(date +%F_%H%M).tar.gz"
  $DOCKER compose exec -T web tar -czf - -C /app/media . > "$MEDIA"
  aws s3 cp "$MEDIA" "s3://$BUCKET/backups/media/$(basename "$MEDIA")" --sse AES256 --only-show-errors
  echo "Backup dos arquivos de vistoria enviado ao S3 privado."
elif [ "$ENVIAR_S3" != "1" ]; then
  echo "Envio de backup ao S3 desativado: backup mantido apenas nesta EC2."
else
  echo "Bucket de backup S3 não configurado: backup mantido apenas nesta EC2."
fi
