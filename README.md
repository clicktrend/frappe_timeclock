# Timeclock

**Kiosk time & attendance terminal for Frappe HR** — turn any tablet (or any device with a browser) into a wall-mounted punch clock. Employees clock in and out via a touch grid + PIN or by holding their QR badge to the camera. Every punch lands as a standard **Employee Checkin**, so HRMS Auto Attendance, timesheets and payroll work out of the box.

No proprietary hardware, no forked doctypes — a small app on top of plain Frappe HR.

## Features

**Kiosk (`/kiosk`)**
- Employee grid → **Kommen/Gehen** (IN/OUT, pre-selected from the last punch) → touch PIN pad
- **QR badge scanning** with the device camera — hybrid: the PIN path always stays available
- Direction is toggled automatically on badge scans, with a **5-second undo**
- **Privacy by default:** the camera scans without showing its image (a badge icon + "scanner ready" pulse instead); a live preview can be enabled in settings. If the camera cannot start, the kiosk says so loudly and falls back to PIN
- Confirmation **sounds** (rising two-tone for IN, falling for OUT), toggleable
- Works on any webcam/browser for testing — camera access requires a secure context (HTTPS or `localhost`)

**Admin (Desk)**
- Own **app tile** in the launcher + **Timeclock workspace**, visible only to System Managers / HR Managers
- Dashboard: **who's-in board** (name, in since, device), number cards (*present now, punches today, missing check-outs, absent today*) and a working-hours chart
- **Time Clock tab on the Employee form:** enable flag, PIN (encrypted at rest, validated server-side), badge ID, inline **QR preview** and **badge printing** (86×54 mm card print format with server-rendered QR)
- **Generate Badge** re-issues a random UUID — a lost card stops working immediately
- `Timeclock Settings` single: camera preview, sounds

**Integration & security**
- Punches are standard **Employee Checkin** records (`log_type`, `time`, `device_id`) — HRMS **Auto Attendance** turns them into Attendance + working hours
- An hourly task keeps `Shift Type.last_sync_of_checkin` current, so realtime kiosk punches are actually processed (normally only biometric sync tools advance that field)
- PIN comparison is constant-time and server-side, with per-employee lockout after 5 failed attempts; unknown badges are rate-limited per device
- Badges are random 128-bit UUIDs, never the employee number
- The kiosk runs under a dedicated user with the **Timeclock Kiosk** role — no desk access, no employee data beyond the grid

## Requirements

- Frappe Framework + [Frappe HR (hrms)](https://github.com/frappe/hrms)

## Installation

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app $URL_OF_THIS_REPO
bench --site yoursite install-app timeclock
bench --site yoursite migrate
```

The built kiosk frontend ships with the repo — no Node step is needed for installation. If you develop on the frontend, rebuild before committing:

```bash
cd apps/timeclock/frontend
npm install
npm run build
```

## Setup

1. **Enable employees:** Employee form → *Time Clock* tab → check *Time Clock Enabled*, set a PIN. For QR: *Generate Badge*, then *Print Badge* (or let employees scan the on-screen QR).
2. **Create the kiosk user:** a Website User (e.g. `kiosk@yourcompany.com`) with only the **Timeclock Kiosk** role.
3. **Auto Attendance (once):** create a `Shift Type` with *Enable Auto Attendance* (working hours from *First Check-in and Last Check-out*, direction *Strictly based on Log Type*) and assign it to your employees — without a shift, checkins are recorded but no Attendance is created.
4. **Open the kiosk:** log in as the kiosk user and open `https://yoursite/kiosk?device=front-door-1`. The `device` parameter is recorded on every punch and shown on the who's-in board.

### Android tablet (kiosk mode)

Any Android 8+ tablet works. A proven setup:

- [FreeKiosk](https://github.com/RushB-fr/freekiosk) (MIT) as the lockdown shell: WebView mode with the kiosk URL, Device Owner via `adb shell dpm set-device-owner`, boot autostart, admin PIN
- Camera scanning needs a **secure context** — serve the site via HTTPS (or allow the origin explicitly in the shell)
- Enable the vendor's **battery protection / charge limit** — the tablet is plugged in 24/7
- Allow media autoplay in the WebView if you want confirmation sounds without a prior touch

## Development

```bash
# backend: standard bench workflow
bench --site yoursite migrate

# frontend dev server (proxies to your bench)
cd apps/timeclock/frontend
npm run dev
```

Python code is formatted with `ruff` (tabs, line length 110, Frappe conventions).

The kiosk UI is currently German-first; translations are on the roadmap.

## Roadmap

- Wallet passes (Apple/Google) carrying the badge QR
- Offline queue (service worker; punches sync with their original timestamp)
- English/multi-language kiosk UI
- Reduced badge-management view for supervisors without full HR permissions

## License

[GPL-3.0](license.txt)
