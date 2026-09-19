#!/usr/bin/env bash

set -Eeuo pipefail

disk_warn_percent=${DISK_WARN_PERCENT:-80}
memory_warn_mib=${MEMORY_WARN_MIB:-100}
temperature_warn_millic=${TEMPERATURE_WARN_MILLIC:-75000}
status_file=/run/smarthome-gateway-health
temporary_file=$(mktemp /run/smarthome-gateway-health.XXXXXX)
trap 'rm -f "${temporary_file}"' EXIT

disk_percent=$(df --output=pcent / | tail -n 1 | tr -dc '0-9')
memory_mib=$(awk '/MemAvailable:/ { printf "%d", $2 / 1024 }' /proc/meminfo)
temperature_millic=$(cat /sys/class/thermal/thermal_zone0/temp)
severity=ok
messages=()

if (( disk_percent >= disk_warn_percent )); then
  severity=warning
  messages+=("disk=${disk_percent}%")
fi

if (( memory_mib <= memory_warn_mib )); then
  severity=warning
  messages+=("memory_available=${memory_mib}MiB")
fi

if (( temperature_millic >= temperature_warn_millic )); then
  severity=warning
  messages+=("temperature_millic=${temperature_millic}")
fi

{
  printf 'severity=%s\n' "${severity}"
  printf 'disk_percent=%s\n' "${disk_percent}"
  printf 'memory_available_mib=%s\n' "${memory_mib}"
  printf 'temperature_millic=%s\n' "${temperature_millic}"
  printf 'checked_at=%s\n' "$(date --iso-8601=seconds)"
} >"${temporary_file}"
chmod 0644 "${temporary_file}"
mv "${temporary_file}" "${status_file}"
trap - EXIT

if [[ ${severity} == warning ]]; then
  logger -p daemon.warning -t smarthome-gateway-health -- "${messages[*]}"
else
  logger -p daemon.info -t smarthome-gateway-health -- \
    "disk=${disk_percent}% memory_available=${memory_mib}MiB temperature_millic=${temperature_millic}"
fi
