# PTT Whisper

[🇷🇺 Русский](#-русский) | [🇬🇧 English](#-english)

---

## 🇷🇺 Русский

Голосовой ввод текста для Ubuntu на базе OpenAI Whisper. Удержи клавишу — говори — отпусти: распознанный текст вставится в активное текстовое поле.

### Как это работает

```
[Right Alt удержан]  →  запись с микрофона
[Right Alt отпущен]  →  аудио → Whisper-сервер → текст → буфер обмена → Ctrl+V
```

Визуальный индикатор отображается в нижней части экрана:
- **Белые полоски-эквалайзер** — идёт запись
- **Крутящаяся дуга + «Распознаю...»** — сервер обрабатывает аудио

### Требования

- Ubuntu 22.04+ с GNOME (X11)
- Python 3.10+
- NVIDIA GPU (рекомендуется) или CPU
- `xclip` и `xrandr`:

```bash
sudo apt install xclip x11-xserver-utils
```

### Установка

```bash
git clone git@github.com:vyunolbek/PTT_Whisper.git
cd PTT_Whisper

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

> **Примечание:** библиотека `keyboard` требует доступа к `/dev/input`. Запускай через `sudo` или добавь себя в группу `input`:
> ```bash
> sudo usermod -aG input $USER  # затем перелогиниться
> ```

### Запуск

**1. Запусти Whisper-сервер** (в отдельном терминале):

```bash
source venv/bin/activate
uvicorn whisper_server:app --host 0.0.0.0 --port 8000
```

По умолчанию используется модель `small`. Для смены отредактируй `whisper_server.py`:

```python
model = whisper.load_model("medium")  # tiny | base | small | medium | large
```

**2. Запусти голосовой ввод:**

```bash
sudo ./venv/bin/python voice_input.py
```

При первом запуске появится список микрофонов — выбери нужный. Выбор сохранится в `voice_input_config.json`.

**3. Смена микрофона:**

```bash
sudo ./venv/bin/python voice_input.py --setup
```

**4. Просмотр доступных микрофонов:**

```bash
sudo ./venv/bin/python list_devices.py
```

### Автозапуск через systemd

Для запуска обоих сервисов автоматически после перезагрузки:

```bash
sudo bash install.sh
```

Скрипт:
1. Создаёт venv и устанавливает зависимости (если нужно)
2. Добавляет пользователя в группу `input` (чтобы не нужен был sudo)
3. Устанавливает `whisper-server` как системный сервис
4. Устанавливает `ptt-whisper` как пользовательский сервис
5. Включает lingering, чтобы пользовательские сервисы стартовали до логина

Полезные команды после установки:

```bash
# Логи
sudo journalctl -u whisper-server -f
journalctl --user -u ptt-whisper -f

# Перезапуск
sudo systemctl restart whisper-server
systemctl --user restart ptt-whisper

# Статус
sudo systemctl status whisper-server
systemctl --user status ptt-whisper
```

> **Важно:** после установки перелогинься, чтобы группа `input` вступила в силу.

---

### Настройки

Ключевые параметры в начале `voice_input.py`:

| Параметр | По умолчанию | Описание |
|---|---|---|
| `HOTKEY` | `right alt` | Клавиша для записи |
| `LANGUAGE` | `ru` | Язык распознавания |
| `WHISPER_URL` | `http://localhost:8000/...` | Адрес Whisper-сервера |
| `MIN_AMPLITUDE` | `200` | Минимальный уровень сигнала (фильтр тишины) |

### Структура проекта

```
PTT_Whisper/
├── whisper_server.py        # FastAPI-сервер для распознавания речи
├── voice_input.py           # Главный скрипт: хоткей + запись + вставка
├── voice_overlay.py         # Визуальный индикатор (tkinter)
├── list_devices.py          # Утилита для просмотра аудиоустройств
├── requirements.txt         # Зависимости Python
├── install.sh               # Скрипт установки systemd-сервисов
└── systemd/
    ├── whisper-server.service  # Шаблон системного сервиса
    └── ptt-whisper.service     # Шаблон пользовательского сервиса
```

---

## 🇬🇧 English

Voice-to-text input for Ubuntu powered by OpenAI Whisper. Hold a key, speak, release — the transcribed text is pasted into the active field.

### How it works

```
[Right Alt held]     →  microphone recording starts
[Right Alt released] →  audio → Whisper server → text → clipboard → Ctrl+V
```

A visual overlay appears at the bottom of the screen:
- **White equalizer bars** — recording in progress
- **Spinning arc + "Recognizing..."** — server is processing audio

### Requirements

- Ubuntu 22.04+ with GNOME (X11)
- Python 3.10+
- NVIDIA GPU (recommended) or CPU
- `xclip` and `xrandr`:

```bash
sudo apt install xclip x11-xserver-utils
```

### Installation

```bash
git clone git@github.com:vyunolbek/PTT_Whisper.git
cd PTT_Whisper

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

> **Note:** the `keyboard` library requires access to `/dev/input`. Either run with `sudo` or add yourself to the `input` group:
> ```bash
> sudo usermod -aG input $USER  # then log out and back in
> ```

### Usage

**1. Start the Whisper server** (in a separate terminal):

```bash
source venv/bin/activate
uvicorn whisper_server:app --host 0.0.0.0 --port 8000
```

The default model is `small`. To change it, edit `whisper_server.py`:

```python
model = whisper.load_model("medium")  # tiny | base | small | medium | large
```

**2. Start voice input:**

```bash
sudo ./venv/bin/python voice_input.py
```

On first run you will be prompted to select a microphone. The choice is saved to `voice_input_config.json`.

**3. Change microphone:**

```bash
sudo ./venv/bin/python voice_input.py --setup
```

**4. List available microphones:**

```bash
sudo ./venv/bin/python list_devices.py
```

### Autostart with systemd

To start both services automatically after reboot:

```bash
sudo bash install.sh
```

The script:
1. Creates the venv and installs dependencies (if needed)
2. Adds the user to the `input` group (so `sudo` is no longer required)
3. Installs `whisper-server` as a system service
4. Installs `ptt-whisper` as a user service
5. Enables lingering so user services start before login

Useful commands after installation:

```bash
# Logs
sudo journalctl -u whisper-server -f
journalctl --user -u ptt-whisper -f

# Restart
sudo systemctl restart whisper-server
systemctl --user restart ptt-whisper

# Status
sudo systemctl status whisper-server
systemctl --user status ptt-whisper
```

> **Important:** log out and back in after installation for the `input` group to take effect.

---

### Configuration

Key parameters at the top of `voice_input.py`:

| Parameter | Default | Description |
|---|---|---|
| `HOTKEY` | `right alt` | Push-to-talk key |
| `LANGUAGE` | `ru` | Recognition language |
| `WHISPER_URL` | `http://localhost:8000/...` | Whisper server address |
| `MIN_AMPLITUDE` | `200` | Minimum signal level (silence filter) |

### Project structure

```
PTT_Whisper/
├── whisper_server.py        # FastAPI server for speech recognition
├── voice_input.py           # Main script: hotkey + recording + paste
├── voice_overlay.py         # Visual indicator (tkinter)
├── list_devices.py          # Utility to list audio input devices
├── requirements.txt         # Python dependencies
├── install.sh               # Systemd service installer
└── systemd/
    ├── whisper-server.service  # System service template
    └── ptt-whisper.service     # User service template
```

---

## License

MIT
