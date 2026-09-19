# Клиент `home`

Подключение к Raspberry Pi:

```bash
scripts/device-ssh home rasppi3b
```

Проверка административного доступа:

```bash
scripts/device-ssh home rasppi3b 'sudo -n true && echo sudo-ok'
```
