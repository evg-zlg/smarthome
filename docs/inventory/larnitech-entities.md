# Сущности Larnitech

Источник: API2 `get-devices` с детальным состоянием.
Всего сущностей: **83**.

Полный машиночитаемый снимок: [`larnitech-entities.json`](larnitech-entities.json).

## Помещения и группы

| Группа | Количество |
| --- | ---: |
| EvoHome | 22 |
| Setup | 26 |
| led | 10 |
| Кондер | 21 |
| Щит | 4 |

## Типы

| Тип | Количество |
| --- | ---: |
| `AC` | 1 |
| `co2-sensor` | 1 |
| `com-port` | 1 |
| `current-sensor` | 1 |
| `dimmer-lamp` | 15 |
| `door-sensor` | 2 |
| `humidity-sensor` | 2 |
| `illumination-sensor` | 2 |
| `ir-receiver` | 1 |
| `ir-transmitter` | 1 |
| `jalousie` | 2 |
| `lamp` | 17 |
| `motion-sensor` | 1 |
| `script` | 7 |
| `switch` | 6 |
| `temperature-sensor` | 14 |
| `valve-heating` | 1 |
| `virtual` | 8 |

## Полный перечень

Состояние — снимок на момент выгрузки, а не постоянная характеристика.

| Адрес | Группа | Название | Тип | Состояние |
| --- | --- | --- | --- | --- |
| `315:11` | EvoHome | IR transmitter | `ir-transmitter` | `{"state":"undefined"}` |
| `315:30` | EvoHome | Motion | `motion-sensor` | `{"state":0.0}` |
| `315:31` | EvoHome | Illumination | `illumination-sensor` | `{"state":30.66}` |
| `315:32` | EvoHome | Temperature | `temperature-sensor` | `{"state":24.59}` |
| `315:33` | EvoHome | Humidity | `humidity-sensor` | `{"state":36.07}` |
| `315:36` | EvoHome | CO2 | `co2-sensor` | `{"state":742}` |
| `315:98` | Setup | Temperature | `temperature-sensor` | `{"state":29.77}` |
| `315:246` | EvoHome | ушел | `script` | `{"state":"off","auto-state":true}` |
| `315:250` | EvoHome | Доброе утро | `script` | `{"state":"off","auto-state":true}` |
| `407:1` | Щит | Цепи управления | `lamp` | `{"state":"on","auto-state":true}` |
| `407:2` | Щит | БП LED | `lamp` | `{"state":"on","auto-state":true}` |
| `407:3` | EvoHome | Шторы переговорная | `jalousie` | `{"state":"opened","auto-state":true}` |
| `407:5` | EvoHome | Шторы 1 | `jalousie` | `{"state":"opened","auto-state":true}` |
| `407:7` | Setup | Радиатор | `valve-heating` | `{"state":"off"}` |
| `407:8` | EvoHome | Рабочая зона Л | `lamp` | `{"state":"on","auto-state":true}` |
| `407:9` | EvoHome | Рабочая зона П | `lamp` | `{"state":"on","auto-state":true}` |
| `407:11` | EvoHome | Dimmer | `dimmer-lamp` | `{"state":"on","auto-state":true,"level":100.0}` |
| `407:12` | EvoHome | Dimmer | `dimmer-lamp` | `{"state":"on","auto-state":true,"level":100.0}` |
| `407:13` | EvoHome | Dimmer | `dimmer-lamp` | `{"state":"on","auto-state":true,"level":100.0}` |
| `407:14` | EvoHome | Dimmer | `dimmer-lamp` | `{"state":"on","auto-state":true,"level":100.0}` |
| `407:15` | Setup | Switch 1 | `switch` | `{"state":"undefined"}` |
| `407:16` | Setup | Switch 2 | `switch` | `{"state":"undefined"}` |
| `407:17` | Setup | Switch 3 | `switch` | `{"state":"undefined"}` |
| `407:18` | Setup | Switch 4 | `switch` | `{"state":"undefined"}` |
| `407:19` | Setup | Switch 5 | `switch` | `{"state":"undefined"}` |
| `407:20` | Setup | Switch 6 | `switch` | `{"state":"undefined"}` |
| `407:39` | Щит | Блок Л | `temperature-sensor` | `{"state":24.88}` |
| `407:40` | Щит | Блок П | `temperature-sensor` | `{"state":26.12}` |
| `407:56` | Setup | IR receiver | `ir-receiver` | `{"state":"undefined"}` |
| `407:90` | Setup | Current | `current-sensor` | `{"state":678}` |
| `407:97` | Setup | Temperature | `temperature-sensor` | `{"state":46.93}` |
| `407:98` | Setup | Temperature | `temperature-sensor` | `{"state":42.9}` |
| `407:246` | EvoHome | я пришел | `script` | `{"state":"off","auto-state":true}` |
| `407:247` | EvoHome | я ушел | `script` | `{"state":"off","auto-state":true}` |
| `407:248` | EvoHome | Спокойной ночи | `script` | `{"state":"off","auto-state":true}` |
| `407:250` | EvoHome | Переговорная зона | `dimmer-lamp` | `{"state":"off","auto-state":true,"level":0.0}` |
| `456:1` | Setup | RS485 | `com-port` | `{"state":"undefined"}` |
| `456:46` | EvoHome | темпер 1 | `script` | `{"state":"off","auto-state":true}` |
| `456:47` | EvoHome | темпер | `script` | `{"state":"off","auto-state":true}` |
| `456:48` | Кондер | Сменить адрес | `lamp` | `{"state":"off","auto-state":true}` |
| `456:98` | Setup | Температура | `temperature-sensor` | `{"state":32.8}` |
| `456:230` | Кондер | AC1Код ош. | `virtual` | `{"state":"No error������������������������������������������"}` |
| `456:231` | Кондер | AC1Ошибка | `door-sensor` | `{"state":"closed"}` |
| `456:232` | Кондер | AC1Т.внеш.т. | `temperature-sensor` | `{"state":58.0}` |
| `456:233` | Кондер | AC1Т.внут.т. | `temperature-sensor` | `{"state":23.0}` |
| `456:234` | Кондер | AC1Т.возд.ул | `temperature-sensor` | `{"state":58.0}` |
| `456:235` | Кондер | AC1Т.возд.вн | `temperature-sensor` | `{"state":23.0}` |
| `456:236` | Кондер | AC1Вер.жалюзи | `lamp` | `{"state":"on","auto-state":true}` |
| `456:237` | Кондер | AC1Подкл. | `door-sensor` | `{"state":"opened"}` |
| `456:238` | Кондер | AC1Мягкий поток | `lamp` | `{"state":"off","auto-state":true}` |
| `456:239` | Кондер | AC1Деж.обогрев | `lamp` | `{"state":"off","auto-state":true}` |
| `456:240` | Кондер | AC1Антиплесень | `lamp` | `{"state":"off","auto-state":true}` |
| `456:241` | Кондер | AC1Самоочистка | `lamp` | `{"state":"off","auto-state":true}` |
| `456:242` | Кондер | AC1Ионизация | `lamp` | `{"state":"off","auto-state":true}` |
| `456:243` | Кондер | AC1Сон | `lamp` | `{"state":"off","auto-state":true}` |
| `456:244` | Кондер | AC1Турбо | `lamp` | `{"state":"off","auto-state":true}` |
| `456:245` | Кондер | AC1Эко | `lamp` | `{"state":"off","auto-state":true}` |
| `456:246` | Кондер | AC1Звук.индик. | `lamp` | `{"state":"off","auto-state":true}` |
| `456:247` | Кондер | AC1Тихий | `lamp` | `{"state":"off","auto-state":true}` |
| `456:248` | Кондер | AC1Подсв.экр. | `lamp` | `{"state":"on","auto-state":true}` |
| `456:249` | Кондер | Кондиционер | `AC` | `{"state":"off","auto-state":true,"target":22.0,"current":23.0,"mode":"heat","fan":null,"vane-hor":6,"vane-ver":6}` |
| `500:1` | led | Диммер | `dimmer-lamp` | `{"state":"off","auto-state":true,"level":0.0}` |
| `500:2` | led | Диммер | `dimmer-lamp` | `{"state":"off","auto-state":true,"level":0.0}` |
| `500:3` | led | Диммер | `dimmer-lamp` | `{"state":"off","auto-state":true,"level":0.0}` |
| `500:4` | led | Диммер | `dimmer-lamp` | `{"state":"off","auto-state":true,"level":0.0}` |
| `500:5` | led | Диммер | `dimmer-lamp` | `{"state":"off","auto-state":true,"level":0.0}` |
| `500:6` | led | Диммер | `dimmer-lamp` | `{"state":"off","auto-state":true,"level":0.0}` |
| `500:7` | led | Диммер | `dimmer-lamp` | `{"state":"off","auto-state":true,"level":0.0}` |
| `500:8` | led | Диммер | `dimmer-lamp` | `{"state":"off","auto-state":true,"level":0.0}` |
| `500:97` | Setup | Temperature | `temperature-sensor` | `{"state":20.43}` |
| `500:98` | Setup | Temperature | `temperature-sensor` | `{"state":22.12}` |
| `500:249` | led | Холодный свет | `dimmer-lamp` | `{"state":"off","auto-state":true,"level":0.0}` |
| `500:250` | led | Теплый свет | `dimmer-lamp` | `{"state":"off","auto-state":true,"level":0.0}` |
| `999:1` | Setup |  | `illumination-sensor` | `{"state":94.51}` |
| `999:2` | Setup |  | `humidity-sensor` | `{"state":55.0}` |
| `999:3` | Setup |  | `temperature-sensor` | `{"state":19.0}` |
| `999:4` | Setup | Pressure | `virtual` | `{"state":"764mmHg"}` |
| `999:5` | Setup | Outside | `virtual` | `{"state":"scattered clouds"}` |
| `999:6` | Setup | Weather condition | `virtual` | `{"state":"scattered clouds, temperature: 19°C, humidity: 55%, pressure: 764mmHg, wind 14km/h"}` |
| `999:7` | Setup | Weather forecast | `virtual` | `{"state":"Sun: few clouds, hi: 19°C, low: 11°C. Mon: clear sky, hi: 18°C, low: 10°C. Tue: broken clouds, hi: 20°C, low: 11°C. Wed: light rain, hi: 20°C, low: 12°C. Thu: clear sky, hi: 17°C, low: 7°C. "}` |
| `999:8` | Setup | Code | `virtual` | `{"state":"44"}` |
| `999:9` | Setup | weather | `virtual` | `{"hex":"0x2C3713FC02000EF0001E06130B2000120A1A01140B0902140C2003110700"}` |
| `999:10` | Setup | sunset&sunrise | `virtual` | `{"hex":"0x7B016304"}` |
