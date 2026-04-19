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
echo ""

# ── 1. Виртуальное окружение / Virtual environment ────────────────────────────
if [[ ! -f "$PROJECT_DIR/venv/bin/python" ]]; then
    echo "[1/3] Создаём venv..."
    sudo -u "$CURRENT_USER" python3 -m venv "$PROJECT_DIR/venv"
    sudo -u "$CURRENT_USER" "$PROJECT_DIR/venv/bin/pip" install -r "$PROJECT_DIR/requirements.txt"
else
    echo "[1/3] venv уже существует, пропускаем."
fi

# ── 2. Системный сервис Whisper-сервера / System service for Whisper ─────────
echo "[2/3] Устанавливаем whisper-server.service..."
sed \
    -e "s|{{USER}}|$CURRENT_USER|g" \
    -e "s|{{PROJECT_DIR}}|$PROJECT_DIR|g" \
    "$PROJECT_DIR/systemd/whisper-server.service" \
    > /etc/systemd/system/whisper-server.service

systemctl daemon-reload
systemctl enable whisper-server.service
systemctl restart whisper-server.service
echo "      whisper-server.service запущен."

# ── 3. Системный сервис голосового ввода / System service for PTT ────────────
echo "[3/3] Устанавливаем ptt-whisper.service..."
sed \
    -e "s|{{PROJECT_DIR}}|$PROJECT_DIR|g" \
    -e "s|{{DISPLAY}}|$DISPLAY_VAR|g" \
    -e "s|{{XAUTHORITY}}|$XAUTH_VAR|g" \
    "$PROJECT_DIR/systemd/ptt-whisper.service" \
    > /etc/systemd/system/ptt-whisper.service

systemctl daemon-reload
systemctl enable ptt-whisper.service
systemctl restart ptt-whisper.service
echo "      ptt-whisper.service запущен."

echo ""
echo "=== Установка завершена / Installation complete ==="
echo ""
echo "Полезные команды / Useful commands:"
echo "  Логи сервера    : sudo journalctl -u whisper-server -f"
echo "  Логи PTT        : sudo journalctl -u ptt-whisper -f"
echo "  Перезапуск PTT  : sudo systemctl restart ptt-whisper"
echo "  Остановить всё  : sudo systemctl stop ptt-whisper whisper-server"
