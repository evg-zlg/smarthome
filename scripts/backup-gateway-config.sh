#!/usr/bin/env bash

set -Eeuo pipefail

backup_dir=/var/backups/smarthome
retention_days=${BACKUP_RETENTION_DAYS:-7}
timestamp=$(date --utc +%Y%m%dT%H%M%SZ)
archive="${backup_dir}/gateway-config-${timestamp}.tar.gz"

install -d -o root -g root -m 0700 "${backup_dir}"

paths=(
  etc/mosquitto/mosquitto.conf
  etc/mosquitto/conf.d/10-local-bootstrap.conf
  etc/nginx/nginx.conf
  etc/nginx/sites-available/smarthome
  etc/systemd/journald.conf.d/90-smarthome-limits.conf
  etc/systemd/system/smarthome-gateway.service
  etc/systemd/system/smarthome-gateway-health.service
  etc/systemd/system/smarthome-gateway-health.timer
  etc/systemd/system/smarthome-gateway-config-backup.service
  etc/systemd/system/smarthome-gateway-config-backup.timer
  opt/smarthome-gateway/app.py
)

existing_paths=()
for path in "${paths[@]}"; do
  if [[ -e /${path} ]]; then
    existing_paths+=("${path}")
  fi
done

tar --create --gzip --file "${archive}" --directory / "${existing_paths[@]}"
chmod 0600 "${archive}"
find "${backup_dir}" -maxdepth 1 -type f -name 'gateway-config-*.tar.gz' \
  -mtime "+${retention_days}" -delete

echo "${archive}"
