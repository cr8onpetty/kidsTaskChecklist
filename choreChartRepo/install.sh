#!/usr/bin/env bash
# Chore Chart installer for Raspberry Pi OS (Desktop). Run from this folder:
#   bash install.sh
# It will:
#   1. install Chromium + emoji font (if missing)
#   2. run the chore server automatically at boot (systemd service "chore-chart")
#   3. open the chart full-screen (kiosk mode) when the desktop starts
#   4. stop the screen from going blank
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
APP="$DIR/app"
ME="$(whoami)"

echo "==> Installing packages"
sudo apt-get update -qq
if ! command -v chromium >/dev/null && ! command -v chromium-browser >/dev/null; then
  sudo apt-get install -y chromium || sudo apt-get install -y chromium-browser
fi
sudo apt-get install -y fonts-noto-color-emoji python3

echo "==> Creating the chore-chart service"
sudo tee /etc/systemd/system/chore-chart.service >/dev/null <<EOF
[Unit]
Description=Chore Chart server
After=network.target

[Service]
User=$ME
WorkingDirectory=$APP
ExecStart=/usr/bin/python3 $APP/server.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload
sudo systemctl enable --now chore-chart

echo "==> Setting up full-screen display at login"
chmod +x "$DIR/kiosk.sh"
mkdir -p "$HOME/.config/autostart"
cat > "$HOME/.config/autostart/chore-chart.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Chore Chart
Exec=$DIR/kiosk.sh
X-GNOME-Autostart-enabled=true
EOF

echo "==> Turning off screen blanking"
sudo raspi-config nonint do_blanking 1 || echo "   (couldn't change blanking; set it in raspi-config > Display Options)"

echo
echo "Done! Timezone is: $(timedatectl show -p Timezone --value)"
echo "  (If that's wrong, fix it with: sudo raspi-config  > Localisation Options > Timezone)"
echo "Reboot to start the chart full-screen:  sudo reboot"
echo "From another computer on your Wi-Fi:   http://$(hostname).local:8080"
