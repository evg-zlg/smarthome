# Сущности Larnitech

Источник: API2 `get-devices` с детальным состоянием.
Всего адресуемых каналов API2: **263**. Это не количество физических устройств:
один прибор может состоять из десятков каналов команд, параметров и состояний.

Полный машиночитаемый снимок: [`larnitech-entities.json`](larnitech-entities.json).

## Помещения и группы

| Группа | Количество |
| --- | ---: |
| EvoHome | 22 |
| Setup | 26 |
| led | 10 |
| Кондер | 201 |
| Щит | 4 |

## Типы

| Тип | Количество |
| --- | ---: |
| `AC` | 10 |
| `co2-sensor` | 1 |
| `com-port` | 1 |
| `current-sensor` | 1 |
| `dimmer-lamp` | 15 |
| `door-sensor` | 20 |
| `humidity-sensor` | 2 |
| `illumination-sensor` | 2 |
| `ir-receiver` | 1 |
| `ir-transmitter` | 1 |
| `jalousie` | 2 |
| `lamp` | 125 |
| `motion-sensor` | 1 |
| `script` | 7 |
| `switch` | 6 |
| `temperature-sensor` | 50 |
| `valve-heating` | 1 |
| `virtual` | 17 |

## Полный перечень

Состояние — снимок на момент выгрузки, а не постоянная характеристика.

| Адрес | Группа | Название | Тип | Состояние |
| --- | --- | --- | --- | --- |
| `315:11` | EvoHome | IR transmitter | `ir-transmitter` | `{"state":"undefined"}` |
| `315:30` | EvoHome | Motion | `motion-sensor` | `{"state":14.61}` |
| `315:31` | EvoHome | Illumination | `illumination-sensor` | `{"state":31.0}` |
| `315:32` | EvoHome | Temperature | `temperature-sensor` | `{"state":24.7}` |
| `315:33` | EvoHome | Humidity | `humidity-sensor` | `{"state":36.28}` |
| `315:36` | EvoHome | CO2 | `co2-sensor` | `{"state":847}` |
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
| `407:39` | Щит | Блок Л | `temperature-sensor` | `{"state":24.94}` |
| `407:40` | Щит | Блок П | `temperature-sensor` | `{"state":26.12}` |
| `407:56` | Setup | IR receiver | `ir-receiver` | `{"state":"undefined"}` |
| `407:90` | Setup | Current | `current-sensor` | `{"state":771}` |
| `407:97` | Setup | Temperature | `temperature-sensor` | `{"state":46.53}` |
| `407:98` | Setup | Temperature | `temperature-sensor` | `{"state":43.61}` |
| `407:246` | EvoHome | я пришел | `script` | `{"state":"off","auto-state":true}` |
| `407:247` | EvoHome | я ушел | `script` | `{"state":"off","auto-state":true}` |
| `407:248` | EvoHome | Спокойной ночи | `script` | `{"state":"off","auto-state":true}` |
| `407:250` | EvoHome | Переговорная зона | `dimmer-lamp` | `{"state":"off","auto-state":true,"level":0.0}` |
| `456:1` | Setup | RS485 | `com-port` | `{"state":"undefined"}` |
| `456:46` | EvoHome | темпер 1 | `script` | `{"state":"off","auto-state":true}` |
| `456:47` | EvoHome | темпер | `script` | `{"state":"off","auto-state":true}` |
| `456:48` | Кондер | Сменить адрес | `lamp` | `{"state":"off","auto-state":true}` |
| `456:49` | Кондер | AC10Код ош. | `virtual` | `{"state":""}` |
| `456:50` | Кондер | AC10Ошибка | `door-sensor` | `{"state":"closed"}` |
| `456:51` | Кондер | AC10Т.внеш.т. | `temperature-sensor` | `{"state":0.0}` |
| `456:52` | Кондер | AC10Т.внут.т. | `temperature-sensor` | `{"state":0.0}` |
| `456:53` | Кондер | AC10Т.возд.ул | `temperature-sensor` | `{"state":0.0}` |
| `456:54` | Кондер | AC10Т.возд.вн | `temperature-sensor` | `{"state":0.0}` |
| `456:55` | Кондер | AC10Вер.жалюзи | `lamp` | `{"state":"off","auto-state":true}` |
| `456:56` | Кондер | AC10Подкл. | `door-sensor` | `{"state":"closed"}` |
| `456:57` | Кондер | AC10Мягкий поток | `lamp` | `{"state":"off","auto-state":true}` |
| `456:58` | Кондер | AC10Деж.обогрев | `lamp` | `{"state":"off","auto-state":true}` |
| `456:59` | Кондер | AC10Антиплесень | `lamp` | `{"state":"off","auto-state":true}` |
| `456:60` | Кондер | AC10Самоочистка | `lamp` | `{"state":"off","auto-state":true}` |
| `456:61` | Кондер | AC10Ионизация | `lamp` | `{"state":"off","auto-state":true}` |
| `456:62` | Кондер | AC10Сон | `lamp` | `{"state":"off","auto-state":true}` |
| `456:63` | Кондер | AC10Турбо | `lamp` | `{"state":"off","auto-state":true}` |
| `456:64` | Кондер | AC10Эко | `lamp` | `{"state":"off","auto-state":true}` |
| `456:65` | Кондер | AC10Звук.индик. | `lamp` | `{"state":"off","auto-state":true}` |
| `456:66` | Кондер | AC10Тихий | `lamp` | `{"state":"off","auto-state":true}` |
| `456:67` | Кондер | AC10Подсв.экр. | `lamp` | `{"state":"off","auto-state":true}` |
| `456:68` | Кондер | AC 10 | `AC` | `{"state":"off","auto-state":true,"target":16.0,"current":0.0,"mode":"fan","fan":"auto","vane-hor":0,"vane-ver":0}` |
| `456:69` | Кондер | AC9Код ош. | `virtual` | `{"state":""}` |
| `456:70` | Кондер | AC9Ошибка | `door-sensor` | `{"state":"closed"}` |
| `456:71` | Кондер | AC9Т.внеш.т. | `temperature-sensor` | `{"state":0.0}` |
| `456:72` | Кондер | AC9Т.внут.т. | `temperature-sensor` | `{"state":0.0}` |
| `456:73` | Кондер | AC9Т.возд.ул | `temperature-sensor` | `{"state":0.0}` |
| `456:74` | Кондер | AC9Т.возд.вн | `temperature-sensor` | `{"state":0.0}` |
| `456:75` | Кондер | AC9Вер.жалюзи | `lamp` | `{"state":"off","auto-state":true}` |
| `456:76` | Кондер | AC9Подкл. | `door-sensor` | `{"state":"closed"}` |
| `456:77` | Кондер | AC9Мягкий поток | `lamp` | `{"state":"off","auto-state":true}` |
| `456:78` | Кондер | AC9Деж.обогрев | `lamp` | `{"state":"off","auto-state":true}` |
| `456:79` | Кондер | AC9Антиплесень | `lamp` | `{"state":"off","auto-state":true}` |
| `456:80` | Кондер | AC9Самоочистка | `lamp` | `{"state":"off","auto-state":true}` |
| `456:81` | Кондер | AC9Ионизация | `lamp` | `{"state":"off","auto-state":true}` |
| `456:82` | Кондер | AC9Сон | `lamp` | `{"state":"off","auto-state":true}` |
| `456:83` | Кондер | AC9Турбо | `lamp` | `{"state":"off","auto-state":true}` |
| `456:84` | Кондер | AC9Эко | `lamp` | `{"state":"off","auto-state":true}` |
| `456:85` | Кондер | AC9Звук.индик. | `lamp` | `{"state":"off","auto-state":true}` |
| `456:86` | Кондер | AC9Тихий | `lamp` | `{"state":"off","auto-state":true}` |
| `456:87` | Кондер | AC9Подсв.экр. | `lamp` | `{"state":"off","auto-state":true}` |
| `456:88` | Кондер | AC 9 | `AC` | `{"state":"off","auto-state":true,"target":16.0,"current":0.0,"mode":"fan","fan":"auto","vane-hor":0,"vane-ver":0}` |
| `456:89` | Кондер | AC8Код ош. | `virtual` | `{"state":""}` |
| `456:90` | Кондер | AC8Ошибка | `door-sensor` | `{"state":"closed"}` |
| `456:91` | Кондер | AC8Т.внеш.т. | `temperature-sensor` | `{"state":0.0}` |
| `456:92` | Кондер | AC8Т.внут.т. | `temperature-sensor` | `{"state":0.0}` |
| `456:93` | Кондер | AC8Т.возд.ул | `temperature-sensor` | `{"state":0.0}` |
| `456:94` | Кондер | AC8Т.возд.вн | `temperature-sensor` | `{"state":0.0}` |
| `456:95` | Кондер | AC8Вер.жалюзи | `lamp` | `{"state":"off","auto-state":true}` |
| `456:96` | Кондер | AC8Подкл. | `door-sensor` | `{"state":"closed"}` |
| `456:97` | Кондер | AC8Мягкий поток | `lamp` | `{"state":"off","auto-state":true}` |
| `456:98` | Setup | Температура | `temperature-sensor` | `{"state":32.57}` |
| `456:99` | Кондер | AC8Деж.обогрев | `lamp` | `{"state":"off","auto-state":true}` |
| `456:100` | Кондер | AC8Антиплесень | `lamp` | `{"state":"off","auto-state":true}` |
| `456:101` | Кондер | AC8Самоочистка | `lamp` | `{"state":"off","auto-state":true}` |
| `456:102` | Кондер | AC8Ионизация | `lamp` | `{"state":"off","auto-state":true}` |
| `456:103` | Кондер | AC8Сон | `lamp` | `{"state":"off","auto-state":true}` |
| `456:104` | Кондер | AC8Турбо | `lamp` | `{"state":"off","auto-state":true}` |
| `456:105` | Кондер | AC8Эко | `lamp` | `{"state":"off","auto-state":true}` |
| `456:106` | Кондер | AC8Звук.индик. | `lamp` | `{"state":"off","auto-state":true}` |
| `456:107` | Кондер | AC8Тихий | `lamp` | `{"state":"off","auto-state":true}` |
| `456:108` | Кондер | AC8Подсв.экр. | `lamp` | `{"state":"off","auto-state":true}` |
| `456:109` | Кондер | AC 8 | `AC` | `{"state":"off","auto-state":true,"target":16.0,"current":0.0,"mode":"fan","fan":"auto","vane-hor":0,"vane-ver":0}` |
| `456:110` | Кондер | AC7Код ош. | `virtual` | `{"state":""}` |
| `456:111` | Кондер | AC7Ошибка | `door-sensor` | `{"state":"closed"}` |
| `456:112` | Кондер | AC7Т.внеш.т. | `temperature-sensor` | `{"state":0.0}` |
| `456:113` | Кондер | AC7Т.внут.т. | `temperature-sensor` | `{"state":0.0}` |
| `456:114` | Кондер | AC7Т.возд.ул | `temperature-sensor` | `{"state":0.0}` |
| `456:115` | Кондер | AC7Т.возд.вн | `temperature-sensor` | `{"state":0.0}` |
| `456:116` | Кондер | AC7Вер.жалюзи | `lamp` | `{"state":"off","auto-state":true}` |
| `456:117` | Кондер | AC7Подкл. | `door-sensor` | `{"state":"closed"}` |
| `456:118` | Кондер | AC7Мягкий поток | `lamp` | `{"state":"off","auto-state":true}` |
| `456:119` | Кондер | AC7Деж.обогрев | `lamp` | `{"state":"off","auto-state":true}` |
| `456:120` | Кондер | AC7Антиплесень | `lamp` | `{"state":"off","auto-state":true}` |
| `456:121` | Кондер | AC7Самоочистка | `lamp` | `{"state":"off","auto-state":true}` |
| `456:122` | Кондер | AC7Ионизация | `lamp` | `{"state":"off","auto-state":true}` |
| `456:123` | Кондер | AC7Сон | `lamp` | `{"state":"off","auto-state":true}` |
| `456:124` | Кондер | AC7Турбо | `lamp` | `{"state":"off","auto-state":true}` |
| `456:125` | Кондер | AC7Эко | `lamp` | `{"state":"off","auto-state":true}` |
| `456:126` | Кондер | AC7Звук.индик. | `lamp` | `{"state":"off","auto-state":true}` |
| `456:127` | Кондер | AC7Тихий | `lamp` | `{"state":"off","auto-state":true}` |
| `456:128` | Кондер | AC7Подсв.экр. | `lamp` | `{"state":"off","auto-state":true}` |
| `456:129` | Кондер | AC 7 | `AC` | `{"state":"off","auto-state":true,"target":16.0,"current":0.0,"mode":"fan","fan":"auto","vane-hor":0,"vane-ver":0}` |
| `456:130` | Кондер | AC6Код ош. | `virtual` | `{"state":""}` |
| `456:131` | Кондер | AC6Ошибка | `door-sensor` | `{"state":"closed"}` |
| `456:132` | Кондер | AC6Т.внеш.т. | `temperature-sensor` | `{"state":0.0}` |
| `456:133` | Кондер | AC6Т.внут.т. | `temperature-sensor` | `{"state":0.0}` |
| `456:134` | Кондер | AC6Т.возд.ул | `temperature-sensor` | `{"state":0.0}` |
| `456:135` | Кондер | AC6Т.возд.вн | `temperature-sensor` | `{"state":0.0}` |
| `456:136` | Кондер | AC6Вер.жалюзи | `lamp` | `{"state":"off","auto-state":true}` |
| `456:137` | Кондер | AC6Подкл. | `door-sensor` | `{"state":"closed"}` |
| `456:138` | Кондер | AC6Мягкий поток | `lamp` | `{"state":"off","auto-state":true}` |
| `456:139` | Кондер | AC6Деж.обогрев | `lamp` | `{"state":"off","auto-state":true}` |
| `456:140` | Кондер | AC6Антиплесень | `lamp` | `{"state":"off","auto-state":true}` |
| `456:141` | Кондер | AC6Самоочистка | `lamp` | `{"state":"off","auto-state":true}` |
| `456:142` | Кондер | AC6Ионизация | `lamp` | `{"state":"off","auto-state":true}` |
| `456:143` | Кондер | AC6Сон | `lamp` | `{"state":"off","auto-state":true}` |
| `456:144` | Кондер | AC6Турбо | `lamp` | `{"state":"off","auto-state":true}` |
| `456:145` | Кондер | AC6Эко | `lamp` | `{"state":"off","auto-state":true}` |
| `456:146` | Кондер | AC6Звук.индик. | `lamp` | `{"state":"off","auto-state":true}` |
| `456:147` | Кондер | AC6Тихий | `lamp` | `{"state":"off","auto-state":true}` |
| `456:148` | Кондер | AC6Подсв.экр. | `lamp` | `{"state":"off","auto-state":true}` |
| `456:149` | Кондер | AC 6 | `AC` | `{"state":"off","auto-state":true,"target":16.0,"current":0.0,"mode":"fan","fan":"auto","vane-hor":0,"vane-ver":0}` |
| `456:150` | Кондер | AC5Код ош. | `virtual` | `{"state":""}` |
| `456:151` | Кондер | AC5Ошибка | `door-sensor` | `{"state":"closed"}` |
| `456:152` | Кондер | AC5Т.внеш.т. | `temperature-sensor` | `{"state":0.0}` |
| `456:153` | Кондер | AC5Т.внут.т. | `temperature-sensor` | `{"state":0.0}` |
| `456:154` | Кондер | AC5Т.возд.ул | `temperature-sensor` | `{"state":0.0}` |
| `456:155` | Кондер | AC5Т.возд.вн | `temperature-sensor` | `{"state":0.0}` |
| `456:156` | Кондер | AC5Вер.жалюзи | `lamp` | `{"state":"off","auto-state":true}` |
| `456:157` | Кондер | AC5Подкл. | `door-sensor` | `{"state":"closed"}` |
| `456:158` | Кондер | AC5Мягкий поток | `lamp` | `{"state":"off","auto-state":true}` |
| `456:159` | Кондер | AC5Деж.обогрев | `lamp` | `{"state":"off","auto-state":true}` |
| `456:160` | Кондер | AC5Антиплесень | `lamp` | `{"state":"off","auto-state":true}` |
| `456:161` | Кондер | AC5Самоочистка | `lamp` | `{"state":"off","auto-state":true}` |
| `456:162` | Кондер | AC5Ионизация | `lamp` | `{"state":"off","auto-state":true}` |
| `456:163` | Кондер | AC5Сон | `lamp` | `{"state":"off","auto-state":true}` |
| `456:164` | Кондер | AC5Турбо | `lamp` | `{"state":"off","auto-state":true}` |
| `456:165` | Кондер | AC5Эко | `lamp` | `{"state":"off","auto-state":true}` |
| `456:166` | Кондер | AC5Звук.индик. | `lamp` | `{"state":"off","auto-state":true}` |
| `456:167` | Кондер | AC5Тихий | `lamp` | `{"state":"off","auto-state":true}` |
| `456:168` | Кондер | AC5Подсв.экр. | `lamp` | `{"state":"off","auto-state":true}` |
| `456:169` | Кондер | AC 5 | `AC` | `{"state":"off","auto-state":true,"target":16.0,"current":0.0,"mode":"fan","fan":"auto","vane-hor":0,"vane-ver":0}` |
| `456:170` | Кондер | AC4Код ош. | `virtual` | `{"state":""}` |
| `456:171` | Кондер | AC4Ошибка | `door-sensor` | `{"state":"closed"}` |
| `456:172` | Кондер | AC4Т.внеш.т. | `temperature-sensor` | `{"state":0.0}` |
| `456:173` | Кондер | AC4Т.внут.т. | `temperature-sensor` | `{"state":0.0}` |
| `456:174` | Кондер | AC4Т.возд.ул | `temperature-sensor` | `{"state":0.0}` |
| `456:175` | Кондер | AC4Т.возд.вн | `temperature-sensor` | `{"state":0.0}` |
| `456:176` | Кондер | AC4Вер.жалюзи | `lamp` | `{"state":"off","auto-state":true}` |
| `456:177` | Кондер | AC4Подкл. | `door-sensor` | `{"state":"closed"}` |
| `456:178` | Кондер | AC4Мягкий поток | `lamp` | `{"state":"off","auto-state":true}` |
| `456:179` | Кондер | AC4Деж.обогрев | `lamp` | `{"state":"off","auto-state":true}` |
| `456:180` | Кондер | AC4Антиплесень | `lamp` | `{"state":"off","auto-state":true}` |
| `456:181` | Кондер | AC4Самоочистка | `lamp` | `{"state":"off","auto-state":true}` |
| `456:182` | Кондер | AC4Ионизация | `lamp` | `{"state":"off","auto-state":true}` |
| `456:183` | Кондер | AC4Сон | `lamp` | `{"state":"off","auto-state":true}` |
| `456:184` | Кондер | AC4Турбо | `lamp` | `{"state":"off","auto-state":true}` |
| `456:185` | Кондер | AC4Эко | `lamp` | `{"state":"off","auto-state":true}` |
| `456:186` | Кондер | AC4Звук.индик. | `lamp` | `{"state":"off","auto-state":true}` |
| `456:187` | Кондер | AC4Тихий | `lamp` | `{"state":"off","auto-state":true}` |
| `456:188` | Кондер | AC4Подсв.экр. | `lamp` | `{"state":"off","auto-state":true}` |
| `456:189` | Кондер | AC 4 | `AC` | `{"state":"off","auto-state":true,"target":16.0,"current":0.0,"mode":"fan","fan":"auto","vane-hor":0,"vane-ver":0}` |
| `456:190` | Кондер | AC3Код ош. | `virtual` | `{"state":""}` |
| `456:191` | Кондер | AC3Ошибка | `door-sensor` | `{"state":"closed"}` |
| `456:192` | Кондер | AC3Т.внеш.т. | `temperature-sensor` | `{"state":0.0}` |
| `456:193` | Кондер | AC3Т.внут.т. | `temperature-sensor` | `{"state":0.0}` |
| `456:194` | Кондер | AC3Т.возд.ул | `temperature-sensor` | `{"state":0.0}` |
| `456:195` | Кондер | AC3Т.возд.вн | `temperature-sensor` | `{"state":0.0}` |
| `456:196` | Кондер | AC3Вер.жалюзи | `lamp` | `{"state":"off","auto-state":true}` |
| `456:197` | Кондер | AC3Подкл. | `door-sensor` | `{"state":"closed"}` |
| `456:198` | Кондер | AC3Мягкий поток | `lamp` | `{"state":"off","auto-state":true}` |
| `456:199` | Кондер | AC3Деж.обогрев | `lamp` | `{"state":"off","auto-state":true}` |
| `456:200` | Кондер | AC3Антиплесень | `lamp` | `{"state":"off","auto-state":true}` |
| `456:201` | Кондер | AC3Самоочистка | `lamp` | `{"state":"off","auto-state":true}` |
| `456:202` | Кондер | AC3Ионизация | `lamp` | `{"state":"off","auto-state":true}` |
| `456:203` | Кондер | AC3Сон | `lamp` | `{"state":"off","auto-state":true}` |
| `456:204` | Кондер | AC3Турбо | `lamp` | `{"state":"off","auto-state":true}` |
| `456:205` | Кондер | AC3Эко | `lamp` | `{"state":"off","auto-state":true}` |
| `456:206` | Кондер | AC3Звук.индик. | `lamp` | `{"state":"off","auto-state":true}` |
| `456:207` | Кондер | AC3Тихий | `lamp` | `{"state":"off","auto-state":true}` |
| `456:208` | Кондер | AC3Подсв.экр. | `lamp` | `{"state":"off","auto-state":true}` |
| `456:209` | Кондер | AC 3 | `AC` | `{"state":"off","auto-state":true,"target":16.0,"current":0.0,"mode":"fan","fan":"auto","vane-hor":0,"vane-ver":0}` |
| `456:210` | Кондер | AC2Код ош. | `virtual` | `{"state":""}` |
| `456:211` | Кондер | AC2Ошибка | `door-sensor` | `{"state":"closed"}` |
| `456:212` | Кондер | AC2Т.внеш.т. | `temperature-sensor` | `{"state":0.0}` |
| `456:213` | Кондер | AC2Т.внут.т. | `temperature-sensor` | `{"state":0.0}` |
| `456:214` | Кондер | AC2Т.возд.ул | `temperature-sensor` | `{"state":0.0}` |
| `456:215` | Кондер | AC2Т.возд.вн | `temperature-sensor` | `{"state":0.0}` |
| `456:216` | Кондер | AC2Вер.жалюзи | `lamp` | `{"state":"off","auto-state":true}` |
| `456:217` | Кондер | AC2Подкл. | `door-sensor` | `{"state":"closed"}` |
| `456:218` | Кондер | AC2Мягкий поток | `lamp` | `{"state":"off","auto-state":true}` |
| `456:219` | Кондер | AC2Деж.обогрев | `lamp` | `{"state":"off","auto-state":true}` |
| `456:220` | Кондер | AC2Антиплесень | `lamp` | `{"state":"off","auto-state":true}` |
| `456:221` | Кондер | AC2Самоочистка | `lamp` | `{"state":"off","auto-state":true}` |
| `456:222` | Кондер | AC2Ионизация | `lamp` | `{"state":"off","auto-state":true}` |
| `456:223` | Кондер | AC2Сон | `lamp` | `{"state":"off","auto-state":true}` |
| `456:224` | Кондер | AC2Турбо | `lamp` | `{"state":"off","auto-state":true}` |
| `456:225` | Кондер | AC2Эко | `lamp` | `{"state":"off","auto-state":true}` |
| `456:226` | Кондер | AC2Звук.индик. | `lamp` | `{"state":"off","auto-state":true}` |
| `456:227` | Кондер | AC2Тихий | `lamp` | `{"state":"off","auto-state":true}` |
| `456:228` | Кондер | AC2Подсв.экр. | `lamp` | `{"state":"off","auto-state":true}` |
| `456:229` | Кондер | AC 2 | `AC` | `{"state":"off","auto-state":true,"target":16.0,"current":0.0,"mode":"fan","fan":"auto","vane-hor":0,"vane-ver":0}` |
| `456:230` | Кондер | AC1Код ош. | `virtual` | `{"state":"No error������������������������������������������"}` |
| `456:231` | Кондер | AC1Ошибка | `door-sensor` | `{"state":"closed"}` |
| `456:232` | Кондер | AC1Т.внеш.т. | `temperature-sensor` | `{"state":58.0}` |
| `456:233` | Кондер | AC1Т.внут.т. | `temperature-sensor` | `{"state":23.0}` |
| `456:234` | Кондер | AC1Т.возд.ул | `temperature-sensor` | `{"state":58.0}` |
| `456:235` | Кондер | AC1Т.возд.вн | `temperature-sensor` | `{"state":23.7}` |
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
| `456:249` | Кондер | Кондиционер | `AC` | `{"state":"off","auto-state":true,"target":22.0,"current":23.7,"mode":"heat","fan":null,"vane-hor":6,"vane-ver":6}` |
| `500:1` | led | Диммер | `dimmer-lamp` | `{"state":"off","auto-state":true,"level":0.0}` |
| `500:2` | led | Диммер | `dimmer-lamp` | `{"state":"off","auto-state":true,"level":0.0}` |
| `500:3` | led | Диммер | `dimmer-lamp` | `{"state":"off","auto-state":true,"level":0.0}` |
| `500:4` | led | Диммер | `dimmer-lamp` | `{"state":"off","auto-state":true,"level":0.0}` |
| `500:5` | led | Диммер | `dimmer-lamp` | `{"state":"off","auto-state":true,"level":0.0}` |
| `500:6` | led | Диммер | `dimmer-lamp` | `{"state":"off","auto-state":true,"level":0.0}` |
| `500:7` | led | Диммер | `dimmer-lamp` | `{"state":"off","auto-state":true,"level":0.0}` |
| `500:8` | led | Диммер | `dimmer-lamp` | `{"state":"off","auto-state":true,"level":0.0}` |
| `500:97` | Setup | Temperature | `temperature-sensor` | `{"state":20.45}` |
| `500:98` | Setup | Temperature | `temperature-sensor` | `{"state":22.42}` |
| `500:249` | led | Холодный свет | `dimmer-lamp` | `{"state":"off","auto-state":true,"level":0.0}` |
| `500:250` | led | Теплый свет | `dimmer-lamp` | `{"state":"off","auto-state":true,"level":0.0}` |
| `999:1` | Setup |  | `illumination-sensor` | `{"state":90.75}` |
| `999:2` | Setup |  | `humidity-sensor` | `{"state":55.0}` |
| `999:3` | Setup |  | `temperature-sensor` | `{"state":19.0}` |
| `999:4` | Setup | Pressure | `virtual` | `{"state":"764mmHg"}` |
| `999:5` | Setup | Outside | `virtual` | `{"state":"scattered clouds"}` |
| `999:6` | Setup | Weather condition | `virtual` | `{"state":"scattered clouds, temperature: 19°C, humidity: 55%, pressure: 764mmHg, wind 14km/h"}` |
| `999:7` | Setup | Weather forecast | `virtual` | `{"state":"Sun: few clouds, hi: 19°C, low: 11°C. Mon: clear sky, hi: 18°C, low: 10°C. Tue: broken clouds, hi: 20°C, low: 11°C. Wed: light rain, hi: 20°C, low: 12°C. Thu: clear sky, hi: 17°C, low: 7°C. "}` |
| `999:8` | Setup | Code | `virtual` | `{"state":"44"}` |
| `999:9` | Setup | weather | `virtual` | `{"hex":"0x2C3713FC02000EF0001E06130B2000120A1A01140B0902140C2003110700"}` |
| `999:10` | Setup | sunset&sunrise | `virtual` | `{"hex":"0x7B016304"}` |
