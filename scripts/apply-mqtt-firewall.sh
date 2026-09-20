#!/usr/bin/env bash

set -Eeuo pipefail

table_family=inet
table_name=smarthome_mqtt
rules_file=/etc/smarthome-gateway/smarthome-mqtt.nft

delete_table() {
  if nft list table "${table_family}" "${table_name}" >/dev/null 2>&1; then
    nft delete table "${table_family}" "${table_name}"
  fi
}

case ${1:-} in
  start)
    delete_table
    nft --check --file "${rules_file}"
    nft --file "${rules_file}"
    ;;
  stop)
    delete_table
    ;;
  check)
    nft --check --file "${rules_file}"
    ;;
  *)
    echo "Использование: $0 {start|stop|check}" >&2
    exit 2
    ;;
esac
