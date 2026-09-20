#!/usr/bin/env bash
set -Eeuo pipefail

if [[ ${EUID} -ne 0 ]]; then
  echo "Запустите скрипт от root: sudo $0" >&2
  exit 1
fi

install -d -o root -g smarthome-gateway -m 0750 /etc/smarthome-gateway
gateway_password=$(openssl rand -hex 24)
vakio_password=$(openssl rand -hex 24)
mosquitto_passwd -b -c /etc/mosquitto/passwd gateway "${gateway_password}"
mosquitto_passwd -b /etc/mosquitto/passwd vakio "${vakio_password}"
chown root:mosquitto /etc/mosquitto/passwd
chmod 0640 /etc/mosquitto/passwd

gateway_tmp=$(mktemp)
vakio_tmp=$(mktemp)
trap 'rm -f "${gateway_tmp}" "${vakio_tmp}"' EXIT
printf 'MQTT_USERNAME=gateway\nMQTT_PASSWORD=%s\nVAKIO_TOPIC=vakio\nCONTROL_ENABLED=false\n' "${gateway_password}" >"${gateway_tmp}"
printf 'VAKIO_MQTT_USERNAME=vakio\nVAKIO_MQTT_PASSWORD=%s\n' "${vakio_password}" >"${vakio_tmp}"
install -o root -g smarthome-gateway -m 0640 "${gateway_tmp}" /etc/smarthome-gateway/gateway.env
install -o root -g root -m 0600 "${vakio_tmp}" /etc/smarthome-gateway/vakio-mqtt.env

VAKIO_MQTT_PASSWORD=${vakio_password} /usr/local/sbin/configure-vakio-mqtt
systemctl restart mosquitto smarthome-gateway
echo "MQTT users configured; secrets stored outside Git in /etc/smarthome-gateway"
