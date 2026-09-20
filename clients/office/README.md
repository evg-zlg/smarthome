# Клиент `office`

Подключение к Raspberry Pi:

```bash
scripts/device-ssh office rasppi3b
```

Проверка административного доступа:

```bash
scripts/device-ssh office rasppi3b 'sudo -n true && echo sudo-ok'
```
