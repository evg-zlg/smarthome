# Первичная подготовка Raspberry Pi

## Назначение

Подготовить чистую Raspberry Pi 3B+ как локальный интеграционный узел для
Larnitech и VAKIO. Скрипт обновляет Debian и устанавливает минимальный стек без
Docker и Home Assistant:

- Mosquitto и клиентские MQTT-утилиты;
- Nginx Light;
- Python 3, `venv` и `pip` для будущего интеграционного сервиса;
- базовые диагностические инструменты;
- `unattended-upgrades`.

## Безопасное начальное состояние

- Mosquitto слушает только `127.0.0.1:1883`.
- Анонимный MQTT-доступ запрещён.
- Доступ VAKIO к MQTT из локальной сети пока не включён.
- Nginx публикует только статическую заглушку и `/healthz`.
- API-ключи и пароли скрипт не создаёт и в Git не записывает.

## Запуск

Из корня репозитория на Raspberry Pi:

```bash
sudo bash scripts/bootstrap-raspberry-pi.sh
```

Для текущего устройства подключение и запуск из локального клона выполняются
без интерактивного пароля:

```bash
scripts/device-ssh office rasppi3b 'sudo bash /home/smarthome/smarthome-bootstrap/scripts/bootstrap-raspberry-pi.sh'
```

Обновление системы может потребовать перезагрузки. Скрипт сообщает об этом
строкой `REBOOT_REQUIRED`, но сам устройство не перезагружает.

## Проверка

```bash
systemctl --failed
systemctl status mosquitto nginx
ss -lntp
mosquitto_sub -h 127.0.0.1 -p 1883 -t test
curl --fail http://127.0.0.1/healthz
```

Проверка MQTT без credentials должна завершиться отказом авторизации. Это
ожидаемое начальное поведение.

## Откат

До подключения реального оборудования службы можно отключить:

```bash
sudo systemctl disable --now mosquitto nginx
```

Удаление пакетов не выполняется автоматически, чтобы не затронуть зависимости и
диагностические данные. Перед удалением необходимо отдельно проверить конфигурацию
и журналы.
