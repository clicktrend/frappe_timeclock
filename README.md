# Timeclock

**Kiosk time & attendance terminal for Frappe HR** — turn any tablet (or any device with a browser) into a wall-mounted punch clock. Employees clock in and out via a touch grid + PIN or by holding their QR badge to the camera. Every punch lands as a standard **Employee Checkin**, so HRMS Auto Attendance, timesheets and payroll work out of the box.

No proprietary hardware, no forked doctypes — a small app on top of plain Frappe HR.

## Screenshots

*All names shown are fictional demo data.*

| Idle — clock & badge scan | Employee grid (PIN path) |
| --- | --- |
| ![Idle screen](docs/screenshots/shot-home.png) | ![Employee grid](docs/screenshots/shot-grid.png) |

| PIN entry | Confirmation with undo |
| --- | --- |
| ![PIN entry](docs/screenshots/shot-pin.png) | ![Confirmation](docs/screenshots/shot-confirm.png) |

## Features

**Kiosk (`/kiosk`)**
- **Clock-first idle screen** in a dark terminal look: big clock + date (synced to the **server clock**, so the display always matches the recorded punch time — even on a misconfigured tablet), badge prompt, one tap to the employee grid
- Employee grid with **initials avatars and live presence** (green dot + "seit HH:MM" while clocked in) → **Kommen/Gehen** (pre-selected from the last punch) → touch PIN pad; falls back to the clock after 45 s of inactivity
- **QR badge scanning** with the device camera — active on the idle screen and the grid; hybrid: the PIN path always stays available
- Direction is toggled automatically on badge scans, with a **5-second undo**
- **Privacy by default:** the camera scans without showing its image (a badge icon + "scanner ready" pulse instead); a live preview can be enabled in settings. If the camera cannot start, the kiosk says so loudly and falls back to PIN
- Confirmation **sounds** (rising two-tone for IN, falling for OUT), toggleable
- Works on any webcam/browser for testing — camera access requires a secure context (HTTPS or `localhost`)

**Admin (Desk)**
- Own **app tile** in the launcher + **Timeclock workspace**, visible only to System Managers / HR Managers
- Dashboard: **who's-in board** (name, in since, device), number cards (*present now, punches today, missing check-outs, absent today*) and a working-hours chart
- **Time Clock tab on the Employee form:** enable flag, PIN (encrypted at rest, validated server-side), badge ID, inline **QR preview** and **badge printing** (86×54 mm card print format with server-rendered QR)
- **Generate Badge** re-issues a random UUID — a lost card stops working immediately
- `Timeclock Settings` single: camera preview, sounds, kiosk language (German/English)

**Integration & security**
- Punches are standard **Employee Checkin** records (`log_type`, `time`, `device_id`) — HRMS **Auto Attendance** turns them into Attendance + working hours
- No custom processing and no scheduler jobs of its own: HRMS' *Auto Update Last Sync* option on the Shift Type advances `last_sync_of_checkin` for realtime punches (see Setup)
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
2. **Create the kiosk user** — the shared login for the kiosk device(s):
   - Desk → *New User* → email e.g. `kiosk@yourcompany.com`, user type **Website User** (no desk access), disable the welcome email and set a password
   - assign exactly one role: **Timeclock Kiosk** (created by the app) — it gates the kiosk API and nothing else; the user cannot read employee data beyond the kiosk grid
   - log in once on the kiosk device and open `/kiosk` — the session is long-lived, one kiosk user can serve any number of terminals (tell them apart via the `?device=` parameter)
   - **or skip manual logins entirely with device auto-login:** in *Timeclock Settings* set *Kiosk Auto-Login User* + a *Kiosk Auto-Login Token* (min. 20 chars), then use `/kiosk?device=front-door-1&token=<token>` as the kiosk start URL. Devices heal themselves after reboots and session expiry; regenerating the token locks all devices out instantly. Auto-login refuses any account that has System Manager or lacks the Timeclock Kiosk role
3. **Auto Attendance (once):** create a `Shift Type` with *Enable Auto Attendance* (working hours from *First Check-in and Last Check-out*, direction *Strictly based on Log Type*) and assign it to your employees — without a shift, checkins are recorded but no Attendance is created.
   **On that same Shift Type, also tick "Automatically update Last Sync of Checkin".** You find it in the *Auto Attendance Settings* block, right column, directly below the *Last Sync of Checkin* field. HRMS only processes checkins up to `last_sync_of_checkin`, and that field is normally advanced by a biometric device's sync tool — a kiosk has none, so without this checkbox punches are recorded but **never turn into Attendance**. With it, HRMS' own hourly job advances the field, clamped to the end of each shift.
   *Did it work?* The *Last Sync of Checkin* field above turns read-only once the box is ticked.
4. **Open the kiosk:** log in as the kiosk user and open `https://yoursite/kiosk?device=front-door-1`. The `device` parameter is recorded on every punch and shown on the who's-in board.

### Android tablet (kiosk mode)

Any Android 8+ tablet works. A proven setup — **step-by-step guide incl. all traps: [docs/freekiosk-setup.md](docs/freekiosk-setup.md)**:

#### Tested devices

| Device | Notes |
| --- | --- |
| Desktop browser + webcam | Chrome/Chromium with any standard webcam — handy for development and evaluation (camera needs `localhost` or HTTPS) |
| Samsung Galaxy Tab A11+ (SM-X230, 11″) | ✅ **Verified in production** — wall-mounted with FreeKiosk in Device Owner mode; the front camera reads the 40 mm badge QR in well under a second. 3D-printable wall mount: [MakerWorld — Wall Mount Samsung Tab A11](https://makerworld.com/en/models/2973635-wall-mount-samsung-tab-a11?from=search#profileId-3335232) |

- [FreeKiosk](https://github.com/RushB-fr/freekiosk) (MIT) as the lockdown shell: WebView mode with the kiosk URL (ideally the auto-login URL incl. `&token=`, so nobody ever types credentials on the device), Device Owner via `adb shell dpm set-device-owner`, boot autostart, admin PIN. Note: FreeKiosk's built-in "Website Authentication" only answers HTTP Basic Auth challenges — it cannot fill the Frappe login form; use the token auto-login instead
- Camera scanning needs a **secure context** — serve the site via HTTPS (or allow the origin explicitly in the shell)
- Enable the vendor's **battery protection / charge limit** — the tablet is plugged in 24/7
- Allow media autoplay in the WebView if you want confirmation sounds without a prior touch

## Troubleshooting

**Punches are recorded, but no Attendance is ever created.**
By far the most common one, and it fails silently — nothing errors, Attendance simply never appears. Check the Shift Type in this order:

1. Is an employee actually assigned to the shift? (*Shift Assignment*, or *Default Shift* on the Employee.) No shift → the checkin is stored with an empty `shift` field and auto attendance skips it.
2. Is **Enable Auto Attendance** ticked?
3. Is **Automatically update Last Sync of Checkin** ticked? *(Auto Attendance Settings → right column, below the Last Sync of Checkin field.)* This is the one people miss: HRMS only looks at checkins older than `Last Sync of Checkin`, and that field is normally advanced by a biometric device's sync tool. A kiosk has none, so without the checkbox the field never moves and every punch stays unprocessed.
4. Is **Process Attendance After** set to a date *before* the punches you are waiting for?

Also note Attendance appears only **after the shift has ended**, and the scheduler runs hourly — so do not expect a record mid-shift. To check without waiting:

```bash
bench --site yoursite execute hrms.hr.doctype.shift_type.shift_type.update_last_sync_of_checkin
bench --site yoursite execute hrms.hr.doctype.shift_type.shift_type.process_auto_attendance_for_all_shifts
```

**The camera panel stays empty / no QR is read.**
`getUserMedia` requires a secure context: serve the site over HTTPS, or use `http://localhost` while developing. A camera already claimed by another app also yields an empty panel.

**The Timeclock tile is missing from the desk launcher.**
It is created on app install and re-ensured on every `bench migrate`, so `bench --site yoursite migrate` brings it back. The tile is only visible to System Manager and HR Manager — that is intentional, employees never see the app.

**A user gets "Not permitted" on the kiosk.**
The kiosk API is gated on the **Timeclock Kiosk** role. Website users need exactly that role; System Manager also works, but do not use an admin account for a wall-mounted device.

## Development

```bash
# backend: standard bench workflow
bench --site yoursite migrate

# frontend dev server (proxies to your bench)
cd apps/timeclock/frontend
npm run dev
```

Python code is formatted with `ruff` (tabs, line length 110, Frappe conventions). Backend tests: `bench --site yoursite run-tests --app timeclock`. CI (GitHub Actions) runs lint, the frontend build and the server tests against Frappe v16 + HRMS.

The kiosk UI ships in German and English — switch via *Timeclock Settings → Kiosk Language*. Backend error messages follow the kiosk user's language (German translations included).

## Roadmap

- Wallet passes (Apple/Google) carrying the badge QR
- Offline queue (service worker; punches sync with their original timestamp)
- Reduced badge-management view for supervisors without full HR permissions

## License

[GPL-3.0](license.txt)
