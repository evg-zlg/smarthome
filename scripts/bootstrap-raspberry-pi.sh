#!/usr/bin/env bash

set -Eeuo pipefail

if [[ ${EUID} -ne 0 ]]; then
  echo "Запустите скрипт от root: sudo $0" >&2
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
repo_dir=$(cd -- "${script_dir}/.." && pwd)

apt-get update
apt-get -y full-upgrade

apt-get install -y --no-install-recommends \
  ca-certificates \
  curl \
  git \
  jq \
  mosquitto \
  mosquitto-clients \
  nginx-light \
  python3 \
  python3-pip \
  python3-venv \
  unattended-upgrades

install -d -o root -g root -m 0755 /etc/mosquitto/conf.d
install -o root -g root -m 0644 \
  "${repo_dir}/config/mosquitto/10-local-bootstrap.conf" \
  /etc/mosquitto/conf.d/10-local-bootstrap.conf

install -d -o root -g root -m 0755 /var/www/smarthome
install -o root -g root -m 0644 \
  "${repo_dir}/config/www/index.html" \
  /var/www/smarthome/index.html
install -o root -g root -m 0644 \
  "${repo_dir}/config/nginx/smarthome" \
  /etc/nginx/sites-available/smarthome

rm -f /etc/nginx/sites-enabled/default
ln -sfn /etc/nginx/sites-available/smarthome /etc/nginx/sites-enabled/smarthome

nginx -t

systemctl enable --now mosquitto nginx
systemctl restart mosquitto nginx

systemctl --no-pager --full status mosquitto nginx || true

if [[ -f /var/run/reboot-required ]]; then
  echo
  echo "REBOOT_REQUIRED"
  cat /var/run/reboot-required.pkgs 2>/dev/null || true
else
  echo
  echo "REBOOT_NOT_REQUIRED"
fi
