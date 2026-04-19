# PTT Whisper

Голосовой ввод текста для Ubuntu с использованием OpenAI Whisper. Удержи клавишу — говори — отпусти: распознанный текст вставится в активное текстовое поле.

Voice-to-text input for Ubuntu powered by OpenAI Whisper. Hold a key, speak, release — the transcribed text is pasted into the active field.

---

## Как это работает / How it works

```
[Right Alt удержан]  →  запись с микрофона
[Right Alt отпущен]  →  аудио → Whisper-сервер → текст → буфер обмена → Ctrl+V
```

Визуальный индикатор (оверлей) отображается в нижней части экрана:
- **Белые полоски-эквалайзер** — идёт запись
- **Крутящаяся дуга + «Распознаю...»** — сервер обрабатывает аудио

---

## Требования / Requirements

- Ubuntu 22.04+ с GNOME (X11)
- Python 3.10+
- NVIDIA GPU (рекомендуется) или CPU
- `xclip` — для вставки текста
- `xrandr` — для определения основного монитора

```bash
sudo apt install xclip x11-xserver-utils
```

---

## Установка / Installation

```bash
git clone git@github.com:vyunolbek/PTT_Whisper.git
cd PTT_Whisper

python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt
```

> **Примечание:** `keyboard` требует доступа к `/dev/input`. Запускай через `sudo` или добавь пользователя в группу `input`:
> ```bash
> sudo usermod -aG input $USER   # потом перелогиниться
> ```

---

## Запуск / Usage

### 1. Запусти Whisper-сервер

```bash
source venv/bin/activate
uvicorn whisper_server:app --host 0.0.0.0 --port 8000
```

По умолчанию загружается модель `small`. Для смены модели отредактируй `whisper_server.py`:

```python
model = whisper.load_model("medium")  # tiny | base | small | medium | large
```

### 2. Запусти голосовой ввод

```bash
sudo ./venv/bin/python voice_input.py
```

При первом запуске будет показан список микрофонов — выбери нужный. Выбор сохранится в `voice_input_config.json`.

### 3. Смена микрофона

```bash
sudo ./venv/bin/python voice_input.py --setup
```

### 4. Определение доступных микрофонов

```bash
sudo ./venv/bin/python list_devices.py
```

---

## Настройки / Configuration

Ключевые параметры в начале `voice_input.py`:

| Параметр | По умолчанию | Описание |
|---|---|---|
| `HOTKEY` | `right alt` | Клавиша записи |
| `LANGUAGE` | `ru` | Язык распознавания |
| `WHISPER_URL` | `http://localhost:8000/...` | Адрес Whisper-сервера |
| `MIN_AMPLITUDE` | `200` | Минимальный уровень сигнала (фильтр тишины) |

---

## Структура проекта / Project structure

```
PTT_Whisper/
├── whisper_server.py        # FastAPI-сервер для распознавания речи
├── voice_input.py           # Главный скрипт: хоткей + запись + вставка
├── voice_overlay.py         # Визуальный индикатор (tkinter)
├── list_devices.py          # Утилита для просмотра аудиоустройств
├── requirements.txt         # Зависимости Python
└── voice_input_config.json  # Сохранённый выбор микрофона (создаётся автоматически)
```

---

## Лицензия / License

MIT
