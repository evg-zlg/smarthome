# Эксплуатация базового gateway-контура

## Проверка состояния

```bash
systemctl status \
  smarthome-gateway.service \
  smarthome-gateway-health.timer \
  smarthome-gateway-config-backup.timer \
  mosquitto nginx
systemctl --failed
curl --fail http://127.0.0.1/gateway/healthz
cat /run/smarthome-gateway-health
```

Проверить компактную модель панели без вывода полного массива каналов:

```bash
curl --fail --silent http://127.0.0.1/gateway/map | \
  jq '{status, control_enabled, observed: .observed | {
    services, api_channels, climate, air_conditioner, errors, read_only
  }}'
```

Нормальное состояние допускает `VAKIO: waiting`, пока устройство не передаёт
MQTT-телеметрию. `MQTT: online` при этом подтверждает доступность самого брокера.
`control_enabled` должен оставаться `false`, а `observed.read_only` — `true`.

Статическая панель доступна по `http://192.168.1.183/` и обновляет данные раз в
10 секунд. При замене файлов проверить синтаксис и перезапустить только gateway:

```bash
python3 -m py_compile /opt/smarthome-gateway/app.py
sudo systemctl restart smarthome-gateway
curl --fail http://127.0.0.1/
```

## Мониторинг ресурсов

`smarthome-gateway-health.timer` выполняет проверку каждые пять минут. Пороговые
значения по умолчанию:

- системный раздел: предупреждение от 80%;
- доступная память: предупреждение при 100 MiB и меньше;
- температура CPU: предупреждение от 75 °C.

Последнее состояние находится в `/run/smarthome-gateway-health`. Сообщения
доступны командой:

```bash
journalctl -t smarthome-gateway-health
```

## Журналы

Persistent journal ограничен 128 MiB, 14 днями хранения и резервирует минимум
512 MiB свободного места. Проверка:

```bash
journalctl --disk-usage
systemd-analyze cat-config systemd/journald.conf
```

## Локальный backup конфигурации

Таймер ежедневно создаёт архив несекретной конфигурации в
`/var/backups/smarthome`. Ручной запуск и проверка:

```bash
sudo systemctl start smarthome-gateway-config-backup.service
sudo systemctl status smarthome-gateway-config-backup.service
sudo ls -lh /var/backups/smarthome
```

Архивы старше семи дней удаляются. Они находятся на той же SD-карте и не
заменяют внешний backup после появления постоянной конфигурации и секретов.

## Watchdog

Аппаратный BCM2835 watchdog уже обслуживается systemd. Проверка:

```bash
sudo wdctl
systemd-analyze cat-config systemd/system.conf | grep Watchdog
```

Изменять timeout без отдельного теста восстановления не следует.

## Безопасная остановка каркаса

Каркас не управляет оборудованием. Его можно остановить без остановки MQTT и
Nginx:

```bash
sudo systemctl disable --now smarthome-gateway.service
```

Для возврата:

```bash
sudo systemctl enable --now smarthome-gateway.service
curl --fail http://127.0.0.1/gateway/healthz
```
