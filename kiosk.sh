#!/usr/bin/env bash
# Opens the chore chart full-screen. Started automatically at login (see install.sh).
URL="http://localhost:8080"

# wait (up to ~60s) for the chore server to be ready
for i in $(seq 60); do
  curl -fs "$URL/api/day" >/dev/null && break
  sleep 1
done

BROWSER="$(command -v chromium || command -v chromium-browser)"
exec "$BROWSER" "$URL" \
  --kiosk --noerrdialogs --disable-infobars --no-first-run \
  --disable-session-crashed-bubble --disable-translate \
  --overscroll-history-navigation=0 --disable-pinch \
  --password-store=basic --check-for-update-interval=31536000
