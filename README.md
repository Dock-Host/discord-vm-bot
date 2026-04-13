# Discord VM Bot

Python-бот для управления виртуальными машинами в Proxmox из Discord и деплоя YouTube RTMP loop.

## Команды VM

- `/create-vm vm-name:<str> operating-system:<str> ram:<int> disk:<int> no-timeout:<bool>`
- `/edit-vm vm-name:<str> ram:<int?> disk:<int?> no-timeout:<bool>`
- `/delete-vm vm-name:<str> purge:<bool> no-timeout:<bool>`
- `/preview-vm vm-name:<str> no-timeout:<bool>`
- `/start-vm vm-name:<str> no-timeout:<bool>`
- `/stop-vm vm-name:<str> no-timeout:<bool>`
- `/restart-vm vm-name:<str> no-timeout:<bool>`
- `/pause-vm vm-name:<str> no-timeout:<bool>`
- `/start-vm-background vm-name:<str>`
- `/stop-vm-background vm-name:<str>`
- `/restart-vm-background vm-name:<str>`
- `/pause-vm-background vm-name:<str>`

## Команда видео деплоя

- `/deploy_video-from-rtmp_youtube youtube-url:<str> rtmp-url:<str> create-vm-ubuntu:<bool>`
  - опционально создает VM Ubuntu 24.04 (RAM 8GB, DISK 128GB) и запускает её;
  - скачивает видео через `yt-dlp` (без timeout);
  - запускает `ffmpeg` RTMP loop `while true` (без timeout);
  - запускает preview-screenshot loop: каждую 1 секунду обновляет screenshot (`preview.jpg`), после отправки файл удаляется.

## Быстрый старт

1. Скопируйте `.env.example` в `.env` и заполните значения, включая шаблон `ubuntu-24.04` в `PROXMOX_TEMPLATE_MAP`.
2. Установите зависимости:

```bash
pip install -r requirements.txt
```

3. Установите `ffmpeg` (системный пакет) и убедитесь, что `yt-dlp`/`ffmpeg` доступны в `PATH`.
4. Запустите бота:

```bash
python bot.py
```

## Структура файлов

- `bot.py` — Discord slash-команды, streaming loop, screenshot loop
- `proxmox_client.py` — операции Proxmox API (create/edit/delete/preview/start/stop/restart/pause)
- `config.py` — загрузка конфигурации из переменных окружения
- `requirements.txt` — Python-зависимости
- `.env.example` — пример окружения
