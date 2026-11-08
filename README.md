# Chore Chart for Ashton & Sienna

A touchscreen chore checklist that runs on a Raspberry Pi.

- The **◀ ▶ arrows** (or a swipe) switch between Ashton and Sienna.
- **Morning / Day / Evening** tabs. The tab for the current time of day opens automatically and is marked "NOW".
- Tap a chore to check it off and tap it again to uncheck it. ★ BONUS chores are optional and don't count toward the total.
- Finishing every required chore in a section shows a confetti celebration.
- The **calendar button** (top right) shows past days. Tap a day to see or fix it.
- If nobody touches the screen for 3 minutes, it goes back to today and the current section.

## What you need
- A Raspberry Pi 3, 4 or 5 running **Raspberry Pi OS with Desktop**
- A touchscreen. Any size works; the layout scales from 800×480 up.

## Install (from your Windows PC, over SSH)

1. **Turn on SSH.** In Raspberry Pi Imager, use the settings (gear) to turn on SSH and set a username. On a Pi that's already set up, run `sudo raspi-config` and go to Interface Options → SSH.
2. **Copy the files.** In PowerShell on your PC (replace `pi` with your Pi username):
   ```powershell
   scp "C:\Users\cr8on\OneDrive\Documents\Kids\Chores\chore-chart.zip" pi@raspberrypi.local:~/
   ```
3. **Log in to the Pi and install:**
   ```powershell
   ssh pi@raspberrypi.local
   ```
   ```bash
   unzip chore-chart.zip -d ~/chore-chart
   cd ~/chore-chart
   bash install.sh
   sudo reboot
   ```
After the reboot, the chart opens full-screen by itself.

## Changing chores
Edit `~/chore-chart/app/chores.json`. Each chore can use:
- `"days": ["mon","wed"]`: show the chore only on those days. Leave it out for every day.
- `"bonus": true`: always optional. Use a list of days, such as `"bonus": ["mon","tue"]`, to make it optional only on those days.

The screen picks up changes within 30 seconds. If the chart shows "Problem loading chores", there's a typo (often a missing comma) in the file.

To edit from your PC, the easiest way is **VS Code** with the **Remote - SSH** extension. Connect to `pi@raspberrypi.local` and open the `~/chore-chart` folder.

## Useful commands
| What | Command |
|---|---|
| Restart the server | `sudo systemctl restart chore-chart` |
| Check that it's running | `systemctl status chore-chart` |
| Open from a phone or PC on your Wi-Fi | `http://raspberrypi.local:8080` |
| Exit full-screen on the Pi | Alt+F4 (with a keyboard) |
| Back up the history | copy `~/chore-chart/app/data/history.json` |

Completed chores are saved in `app/data/history.json`, organized by date and then by kid.
