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

В объекте `larnitech` нормальное соединение имеет `status: online`, адрес
`315:36` в `subscribed_addrs` и актуальный `heartbeat_at`. Поле
`last_event_at` меняется только при фактическом событии датчика; отсутствие
изменений CO2 само по себе не означает потерю соединения.

Проверка восстановления подписки и поступления событий:

```bash
journalctl -u smarthome-gateway.service --since today | \
  grep 'Larnitech API2 subscribed\|Larnitech event received'
```

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

## MQTT VAKIO

VAKIO Base Smart использует пустые login/password. Поле `topic` в его
веб-интерфейсе — уникальное имя прибора. Для текущего единственного
прибора используется `vakio`. Проверенные топики текущей ревизии:
`vakio/state`, `vakio/workmode` и `vakio/speed`.

Перед запуском LAN-listener обязательно проверить firewall:

```bash
sudo systemctl status smarthome-mqtt-firewall.service
sudo nft list table inet smarthome_mqtt
```

Должно быть два правила TCP/1883: `accept` только от VAKIO и `reject`
для остальных LAN-адресов. Gateway подключается через loopback с
отдельными credentials.

После подключения сначала нужно увидеть сообщения прибора:

```bash
sudo mosquitto_sub -h 127.0.0.1 -u gateway -P '<пароль>' -t 'vakio/#' -v
```

Команды публикуются в соответствующий топик. Например, скорость 4 —
это payload `4` в `vakio/speed`. Отправлять команду можно только после свежей
телеметрии и с последующим ответом прибора. Gateway подписывается с MQTT v5
`noLocal`, чтобы не принять собственную публикацию за подтверждение.

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
