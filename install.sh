#!/usr/bin/env bash
# Установка PTT Whisper как системных сервисов
# Install PTT Whisper as systemd services
set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CURRENT_USER="$(logname 2>/dev/null || echo "$SUDO_USER")"

if [[ -z "$CURRENT_USER" ]]; then
    echo "Ошибка: не удалось определить пользователя. Запусти через sudo."
    exit 1
fi

USER_HOME=$(eval echo "~$CURRENT_USER")
DISPLAY_VAR="${DISPLAY:-:1}"
XAUTH_VAR="${XAUTHORITY:-$USER_HOME/.Xauthority}"

echo "=== PTT Whisper Install ==="
echo "Пользователь / User : $CURRENT_USER"
echo "Проект / Project    : $PROJECT_DIR"
echo "DISPLAY             : $DISPLAY_VAR"
echo "XAUTHORITY          : $XAUTH_VAR"
echo ""

# ── 1. Виртуальное окружение / Virtual environment ────────────────────────────
if [[ ! -f "$PROJECT_DIR/venv/bin/python" ]]; then
    echo "[1/5] Создаём venv..."
    sudo -u "$CURRENT_USER" python3 -m venv "$PROJECT_DIR/venv"
    sudo -u "$CURRENT_USER" "$PROJECT_DIR/venv/bin/pip" install -r "$PROJECT_DIR/requirements.txt"
else
    echo "[1/5] venv уже существует, пропускаем."
fi

# ── 2. Группа input (для keyboard без sudo) / input group ────────────────────
echo "[2/5] Добавляем $CURRENT_USER в группу input..."
usermod -aG input "$CURRENT_USER"
echo "      Готово. Изменение вступит в силу после перелогинивания."

# ── 3. Системный сервис Whisper-сервера / System service for Whisper ─────────
echo "[3/5] Устанавливаем whisper-server.service..."
sed \
    -e "s|{{USER}}|$CURRENT_USER|g" \
    -e "s|{{PROJECT_DIR}}|$PROJECT_DIR|g" \
    "$PROJECT_DIR/systemd/whisper-server.service" \
    > /etc/systemd/system/whisper-server.service

systemctl daemon-reload
systemctl enable whisper-server.service
systemctl restart whisper-server.service
echo "      whisper-server.service запущен."

# ── 4. Пользовательский сервис голосового ввода / User service for PTT ───────
echo "[4/5] Устанавливаем ptt-whisper.service..."
USER_SYSTEMD_DIR="$USER_HOME/.config/systemd/user"
mkdir -p "$USER_SYSTEMD_DIR"

sed \
    -e "s|{{PROJECT_DIR}}|$PROJECT_DIR|g" \
    -e "s|{{DISPLAY}}|$DISPLAY_VAR|g" \
    -e "s|{{XAUTHORITY}}|$XAUTH_VAR|g" \
    "$PROJECT_DIR/systemd/ptt-whisper.service" \
    > "$USER_SYSTEMD_DIR/ptt-whisper.service"

chown "$CURRENT_USER:$CURRENT_USER" "$USER_SYSTEMD_DIR/ptt-whisper.service"

sudo -u "$CURRENT_USER" systemctl --user daemon-reload
sudo -u "$CURRENT_USER" systemctl --user enable ptt-whisper.service
sudo -u "$CURRENT_USER" systemctl --user restart ptt-whisper.service
echo "      ptt-whisper.service запущен."

# ── 5. Автозапуск пользовательских сервисов при старте системы ───────────────
echo "[5/5] Включаем lingering для $CURRENT_USER..."
loginctl enable-linger "$CURRENT_USER"

echo ""
echo "=== Установка завершена / Installation complete ==="
echo ""
echo "Полезные команды / Useful commands:"
echo "  Логи сервера    : sudo journalctl -u whisper-server -f"
echo "  Логи PTT        : journalctl --user -u ptt-whisper -f"
echo "  Перезапуск PTT  : systemctl --user restart ptt-whisper"
echo "  Остановить всё  : systemctl --user stop ptt-whisper && sudo systemctl stop whisper-server"
echo ""
echo "⚠  Перелогинься, чтобы группа input вступила в силу."
echo "⚠  Log out and back in for the 'input' group to take effect."
