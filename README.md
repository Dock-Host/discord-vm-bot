# Discord VM Bot

Python-бот для управления виртуальными машинами в Proxmox из Discord и деплоя YouTube RTMP loop.

## Команды

- `/create-vm vm-name:<str> operating-system:<str> ram:<int> disk:<int> no-timeout:<bool>`
- `/edit-vm vm-name:<str> ram:<int?> disk:<int?> no-timeout:<bool>`
- `/delete-vm vm-name:<str> purge:<bool> no-timeout:<bool>`
- `/preview-vm vm-name:<str> no-timeout:<bool>`
- `/deploy_video-from-rtmp_youtube youtube-url:<str> rtmp-url:<str>`

## Быстрый старт

1. Скопируйте `.env.example` в `.env` и заполните значения.
2. Установите зависимости:

```bash
pip install -r requirements.txt
```

3. Установите `ffmpeg` (системный пакет) и убедитесь, что он доступен в `PATH`.
4. Запустите бота:

```bash
python bot.py
```

## Структура файлов

- `bot.py` — все Discord slash-команды
- `proxmox_client.py` — операции Proxmox API: create/edit/delete/preview VM
- `config.py` — загрузка конфигурации из переменных окружения
- `requirements.txt` — Python-зависимости
- `.env.example` — пример окружения
