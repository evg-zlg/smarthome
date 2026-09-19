#!/usr/bin/env bash

set -Eeuo pipefail

if [[ ${EUID} -ne 0 ]]; then
  echo "Запустите скрипт от root: sudo $0" >&2
  exit 1
fi

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
repo_dir=$(cd -- "${script_dir}/.." && pwd)

if ! id smarthome-gateway >/dev/null 2>&1; then
  useradd --system --home-dir /nonexistent --shell /usr/sbin/nologin \
    --user-group smarthome-gateway
fi

install -d -o root -g root -m 0755 /opt/smarthome-gateway
install -o root -g root -m 0755 "${repo_dir}/gateway/app.py" \
  /opt/smarthome-gateway/app.py
install -d -o root -g smarthome-gateway -m 0750 /etc/smarthome-gateway
install -d -o root -g root -m 0700 /var/backups/smarthome

install -o root -g root -m 0644 "${repo_dir}/config/nginx/smarthome" \
  /etc/nginx/sites-available/smarthome

install -d -o root -g root -m 0755 /etc/systemd/journald.conf.d
install -o root -g root -m 0644 \
  "${repo_dir}/config/systemd/journald.conf.d/90-smarthome-limits.conf" \
  /etc/systemd/journald.conf.d/90-smarthome-limits.conf

install -o root -g root -m 0755 "${repo_dir}/scripts/check-gateway-health.sh" \
  /usr/local/sbin/check-smarthome-gateway-health
install -o root -g root -m 0755 "${repo_dir}/scripts/backup-gateway-config.sh" \
  /usr/local/sbin/backup-smarthome-gateway-config

for unit in \
  smarthome-gateway.service \
  smarthome-gateway-health.service \
  smarthome-gateway-health.timer \
  smarthome-gateway-config-backup.service \
  smarthome-gateway-config-backup.timer; do
  install -o root -g root -m 0644 \
    "${repo_dir}/config/systemd/system/${unit}" "/etc/systemd/system/${unit}"
done

nginx -t
systemctl daemon-reload
systemctl restart systemd-journald
systemctl reload nginx
systemctl enable --now \
  smarthome-gateway.service \
  smarthome-gateway-health.timer \
  smarthome-gateway-config-backup.timer

systemctl start smarthome-gateway-health.service
systemctl start smarthome-gateway-config-backup.service

systemctl is-active \
  smarthome-gateway.service \
  smarthome-gateway-health.timer \
  smarthome-gateway-config-backup.timer
