---
title: "Базовый шлюз Raspberry Pi"
status: active
verified: 2026-09-19
rfc: ../rfc/larnitech-vakio-raspberry-pi.md
---

# Базовый шлюз Raspberry Pi

## Платформа

- Устройство: Raspberry Pi 3 Model B Plus Rev 1.4.
- ОС: Debian GNU/Linux 13 (trixie), `aarch64`.
- Проверенное ядро после перезагрузки: `6.18.50+rpt-rpi-v8`.
- Системный раздел: 29 GiB, занято около 6.7 GiB на дату проверки.
- Оперативная память: 905 MiB; swap: 904 MiB.
- Основное подключение к LAN: Wi-Fi.

## Установленные службы

| Компонент | Версия | Состояние | Назначение |
| --- | --- | --- | --- |
| Mosquitto | 2.0.21-1 | enabled, active | Локальный MQTT-брокер |
| Mosquitto clients | 2.0.21-1 | установлен | Диагностика MQTT |
| Nginx Light | 1.26.3-3+deb13u9 | enabled, active | HTTP и будущий reverse proxy |
| Python | 3.13.5-1 | установлен | Будущий адаптер Larnitech/VAKIO |
| unattended-upgrades | 2.12 | enabled, active | Автоматические обновления безопасности |

## Сетевые границы

- SSH слушает TCP `22` на LAN-интерфейсах.
- Nginx слушает TCP `80` на IPv4 и IPv6; опубликованы только статическая
  заглушка и `/healthz`.
- Mosquitto слушает TCP `1883` только на `127.0.0.1`.
- Анонимный MQTT-доступ запрещён и фактически отклоняется брокером.
- MQTT-доступ из LAN не включён до появления VAKIO, создания отдельных
  credentials и ACL для подтверждённых топиков.

## Проверенное поведение

- `GET http://127.0.0.1/healthz` возвращает `200` и `ok`.
- Анонимная MQTT-публикация завершается `Connection Refused: not authorised`.
- После обновления и перезагрузки ошибочных systemd units нет.
- Список ожидающих APT-обновлений пуст.
- NTP синхронизирован; системный часовой пояс — `Asia/Yekaterinburg` (UTC+5).

## Известные ограничения

- Ethernet не подключён; постоянный шлюз пока зависит от Wi-Fi.
- Пользователь и ACL MQTT ещё не созданы.
- Интеграционный Python-сервис ещё не реализован.
- Larnitech и VAKIO не подключались и не опрашивались.
