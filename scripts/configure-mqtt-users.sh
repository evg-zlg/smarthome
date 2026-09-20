#!/usr/bin/env bash
set -Eeuo pipefail

if [[ ${EUID} -ne 0 ]]; then
  echo "Запустите скрипт от root: sudo $0" >&2
  exit 1
fi

install -d -o root -g smarthome-gateway -m 0750 /etc/smarthome-gateway
gateway_password=$(openssl rand -hex 24)
mosquitto_passwd -b -c /etc/mosquitto/passwd gateway "${gateway_password}"
chown root:mosquitto /etc/mosquitto/passwd
chmod 0640 /etc/mosquitto/passwd

gateway_tmp=$(mktemp)
trap 'rm -f "${gateway_tmp}"' EXIT
printf 'MQTT_HOST=127.0.0.1\nMQTT_USERNAME=gateway\nMQTT_PASSWORD=%s\nVAKIO_TOPIC=vakio\nCONTROL_ENABLED=true\n' "${gateway_password}" >"${gateway_tmp}"
install -o root -g smarthome-gateway -m 0640 "${gateway_tmp}" /etc/smarthome-gateway/gateway.env

/usr/local/sbin/configure-vakio-mqtt
systemctl restart mosquitto smarthome-gateway
echo "Gateway MQTT user configured; VAKIO listener is anonymous and IP-restricted"
