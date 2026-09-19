#!/usr/bin/env bash

set -Eeuo pipefail

if [[ ${EUID} -ne 0 ]]; then
  echo "Запустите от root: sudo $0 <public-key-file>" >&2
  exit 1
fi

if [[ $# -ne 1 || ! -f $1 ]]; then
  echo "Использование: sudo $0 <public-key-file>" >&2
  exit 2
fi

access_user=smarthome
public_key_file=$1

if ! id "${access_user}" >/dev/null 2>&1; then
  useradd --create-home --shell /bin/bash "${access_user}"
fi

usermod -aG sudo "${access_user}"
install -d -o "${access_user}" -g "${access_user}" -m 0700 "/home/${access_user}/.ssh"
install -o "${access_user}" -g "${access_user}" -m 0600 \
  "${public_key_file}" "/home/${access_user}/.ssh/authorized_keys"

cat >"/etc/sudoers.d/90-${access_user}" <<EOF
${access_user} ALL=(ALL:ALL) NOPASSWD: ALL
EOF
chmod 0440 "/etc/sudoers.d/90-${access_user}"
visudo -cf "/etc/sudoers.d/90-${access_user}"

echo "Доступ настроен для ${access_user}"
