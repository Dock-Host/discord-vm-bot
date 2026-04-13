# Discord VM Bot

Python-бот для управления виртуальными машинами в Proxmox из Discord.

## Команда

`/create-vm vm-name:<str> operating-system:<str> ram:<int> disk:<int> no-timeout:<bool>`

- `vm-name` — имя ВМ
- `operating-system` — шаблон/OS identifier для клонирования
- `ram` — RAM в MB
- `disk` — размер диска в GB
- `no-timeout` — если `true`, бот не ставит timeout для долгой операции

## Быстрый старт

1. Скопируйте `.env.example` в `.env` и заполните значения.
2. Установите зависимости:

```bash
pip install -r requirements.txt
```

3. Запустите бота:

```bash
python bot.py
```

## Структура файлов

- `bot.py` — Discord slash-команда `/create-vm`
- `proxmox_client.py` — клиент для Proxmox API
- `config.py` — загрузка конфигурации из переменных окружения
- `requirements.txt` — зависимости
- `.env.example` — пример окружения
