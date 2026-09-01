#!/bin/bash
# PostgreSQL backup script for MedVerify
# Run via cron: 0 2 * * * /opt/medverify/backup.sh

set -e

BACKUP_DIR="${BACKUP_DIR:-/backups}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"
DB_NAME="${DB_NAME:-medverify}"
DB_USER="${DB_USER:-medverify}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/medverify_${TIMESTAMP}.sql.gz"

mkdir -p "${BACKUP_DIR}"

echo "[$(date)] Starting backup of ${DB_NAME}"

pg_dump -U "${DB_USER}" -h localhost -d "${DB_NAME}" | gzip > "${BACKUP_FILE}"

echo "[$(date)] Backup created: ${BACKUP_FILE}"
echo "[$(date)] Backup size: $(du -h ${BACKUP_FILE} | cut -f1)"

# Remove old backups
find "${BACKUP_DIR}" -name "medverify_*.sql.gz" -mtime +${RETENTION_DAYS} -delete
echo "[$(date)] Old backups cleaned up (retention: ${RETENTION_DAYS} days)"

# Upload to remote storage if configured
if [ -n "${BACKUP_REMOTE_URI}" ]; then
    echo "[$(date)] Uploading to remote storage..."
    rclone copy "${BACKUP_FILE}" "${BACKUP_REMOTE_URI}/" --quiet
    echo "[$(date)] Upload complete"
fi

echo "[$(date)] Backup job complete"
