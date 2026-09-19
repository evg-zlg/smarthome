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

До настройки Larnitech и VAKIO ожидаемый ответ gateway:

```json
{"status":"waiting_for_configuration","larnitech":"not_configured","vakio":"not_configured","control_enabled":false}
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
