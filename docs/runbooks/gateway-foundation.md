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

Нормальное состояние текущего контура: `MQTT: online`, VAKIO `online` только
после свежего сообщения прибора, `control_enabled=false` при активном мосте
Larnitech и `observed.read_only=true` для
карты наблюдения. Управление Larnitech независимо: `scenario_control.enabled`
должно быть `true`, а `allowed=true` — только у семи исследованных адресов
`315:246`, `315:250`, `407:246`, `407:247`, `407:248`, `456:46`, `456:47`.
Это состояние разрешает ручной запуск через панель, но само по себе не запускает
ни один сценарий.

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

Штатные команды Base Smart публикуются как raw payload в `vakio/mode`:
`06000/06001` для питания, `06010`–`06041` для семи режимов и `06501`–`06507`
для скоростей. Их вручную не публикуют: gateway принимает только 15 allowlist-
адресов Larnitech. Gateway подписывается с MQTT v5 `noLocal`, а retained
сообщения не считает свежим подтверждением.

Проверка моста без управления прибором:

```bash
curl --fail --silent http://127.0.0.1/gateway/healthz | \
  jq '{control_enabled, vakio_status: .vakio.status,
    bridge: .vakio_larnitech_bridge}'
```

При `bridge.enabled=true` ожидается `control_enabled=false`: веб-панель не
может обойти Larnitech. Если VAKIO не прислал свежую телеметрию после запуска,
`vakio.status=waiting` является безопасным состоянием, даже если в
`vakio.topics` виден старый retained `state=on`.

Интерфейс берёт текущие значения только из `vakio.confirmed_topics`. Поле
`vakio.topics` предназначено для диагностики retained-снимка и не должно
использоваться для надписи «Включена» или выбранного режима.

При включении режима или скорости из Larnitech gateway сначала отправляет
питание `on` и ожидает новое, не retained подтверждение. Только затем
отправляется выбранный режим или скорость. Поэтому в сценарии Larnitech не
нужно добавлять отдельную строку питания перед `Режим · Ночной`.

## Сценарии Larnitech

Перед включением прочитать
[инвентаризацию сценариев](../inventory/larnitech-scenarios.md). Для полного
запрета достаточно любого из двух условий в `/etc/smarthome-gateway/gateway.env`:

```text
LARNITECH_SCENARIO_CONTROL_ENABLED=false
LARNITECH_SCENARIO_ALLOWLIST=
```

После изменения выполнить restart gateway и проверить карту:

```bash
curl --fail --silent http://127.0.0.1/gateway/map | \
  jq '.scenario_control | {enabled, cooldown_seconds,
    allowed: [.scenarios[] | select(.allowed) | .addr]}'
```

Включать можно только точные адреса из встроенного реестра. Нельзя добавлять
неисследованный адрес «для проверки»: сервис завершится при неизвестном адресе.
Один физический тест выполняется только при наблюдении на объекте и готовности
остановить шторы/свет/кондиционер штатным способом.

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

Остановка gateway убирает управление VAKIO и сценариями Larnitech, но не
останавливает MQTT и Nginx:

```bash
sudo systemctl disable --now smarthome-gateway.service
```

Для возврата:

```bash
sudo systemctl enable --now smarthome-gateway.service
curl --fail http://127.0.0.1/gateway/healthz
```
