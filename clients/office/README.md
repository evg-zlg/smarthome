# Клиент `office`

Архитектура и границы управления описаны в
[концептуальной схеме системы «Офис»](../../docs/architecture/office-system.md).

Подключение к Raspberry Pi:

```bash
scripts/device-ssh office rasppi3b
```

Проверка административного доступа:

```bash
scripts/device-ssh office rasppi3b 'sudo -n true && echo sudo-ok'
```

Доступ к контроллеру Larnitech находится в
`credentials/larnitech/controller.yaml`. Файл содержит адрес панели,
административный логин/пароль, API2 WebSocket URL и существующий API key.
