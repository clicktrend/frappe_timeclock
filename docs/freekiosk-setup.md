# FreeKiosk setup (Android tablet as wall terminal)

Battle-tested procedure for locking an Android tablet down to the Timeclock kiosk
with [FreeKiosk](https://github.com/RushB-fr/freekiosk) (MIT) in **Device Owner**
mode — full lockdown: no notifications, no home/recent buttons, survives reboots.
Verified on a Samsung Galaxy Tab A11+ (SM-X230); any Android 8+ tablet works the
same way.

**You need:** the tablet, a USB cable, a computer with `adb`
([platform-tools](https://developer.android.com/tools/releases/platform-tools) —
no root, no installation beyond unzipping), and the FreeKiosk APK from the
[releases page](https://github.com/RushB-fr/freekiosk/releases).

## 1. Set up the tablet WITHOUT any account

Device Owner can only be activated on a device with **zero user accounts**.

- Walk through the Android setup wizard: connect Wi-Fi, **skip** Google login,
  **skip** the vendor account (Samsung etc.), skip restore/copy offers. No SIM.
- If you already signed in: *Settings → Accounts → remove the account* — a
  factory reset is **not** necessary.

## 2. Enable USB debugging

- *Settings → About tablet → Software information* → tap **Build number 7×**
- *Settings → Developer options* → enable **USB debugging**
- Connect the USB cable and confirm the RSA prompt on the tablet
  (**"Always allow from this computer"**)

Check from the computer — the device must be listed as `device`, not
`unauthorized`:

```bash
adb devices
```

## 3. Install the APK and set Device Owner

```bash
adb install freekiosk-vX.Y.Z.apk
adb shell dpm set-device-owner com.freekiosk/.DeviceAdminReceiver
```

Expected: `Success: Device owner set to package com.freekiosk/.DeviceAdminReceiver`.

### Trap: "there are already some accounts on the device"

The exact reason hides in logcat:

```bash
adb logcat -d | grep -i devicepolicy | tail
# → "Non test-only owner can't be installed with existing accounts."
adb shell dumpsys account | grep "Account {"
```

Two account types show up in practice:

1. **A regular Google/Samsung account** — remove it in
   *Settings → Accounts* (see step 1).
2. **A ghost account left by a Google app**, e.g.
   `Account {name=Meet, type=com.google.android.apps.tachyon}` — Google Meet
   registers a pseudo-account the moment a Google account is added, and it
   **survives** removing the Google account, `pm clear`, disabling the app and
   even a reboot. What finally works: uninstall the app for the current user,
   **then reboot** — Android purges accounts whose authenticator is gone during
   boot:

   ```bash
   adb shell pm uninstall --user 0 com.google.android.apps.tachyon
   adb reboot
   # after boot:
   adb shell dumpsys account | grep -c "Account {"   # must be 0
   adb shell dpm set-device-owner com.freekiosk/.DeviceAdminReceiver
   ```

If `set-device-owner` fails with a generic `Can't set package … as device owner`,
activate the admin receiver first and retry:

```bash
adb shell dpm set-active-admin com.freekiosk/.DeviceAdminReceiver
adb shell dpm set-device-owner com.freekiosk/.DeviceAdminReceiver
```

## 4. Pre-grant the camera permission

The badge scanner needs the camera; granting it via adb avoids any permission
dialog on the locked-down device:

```bash
adb shell pm grant com.freekiosk android.permission.CAMERA
```

## 5. Configure the tablet BEFORE starting kiosk mode

Once kiosk mode runs, the system settings are locked away — do this first:

- **Battery protection / charge limit** (Samsung: *Settings → Battery →
  Battery protection → max. 80 %*) — the tablet is plugged in 24/7.
- Display timeout is handled by FreeKiosk (keep-screen-on option).

## 6. Configure FreeKiosk

1. Open FreeKiosk → initial setup
2. Set the **admin PIN** (4–6 digits — this is your only way back in:
   tap the bottom-right corner **5×**, then enter the PIN)
3. Mode **Website/URL**, target URL = the kiosk auto-login URL:

   ```
   https://your-site/kiosk?device=front-door-1&token=<your token>
   ```

   (Token: *Timeclock Settings → Kiosk Auto-Login* — see the
   [README](../README.md#setup). Tip: instead of typing 40+ cryptic characters
   on the on-screen keyboard, focus the URL field and inject the string from
   the computer: `adb shell input text 'https://…'`.)

4. Enable **autostart on boot** and keep-screen-on
5. **Start Kiosk Mode**

## 7. Smoke test

- Clock screen appears (dark UI, server-synced time)
- Badge scan → punch confirmation + sound
- PIN path: "Clock in without badge" → employee → PIN
- Reboot the tablet → FreeKiosk starts automatically back into the kiosk

## Leaving kiosk mode / undoing Device Owner

Tap the bottom-right corner 5× → admin PIN → settings. To remove Device Owner
entirely: *"Remove Device Owner"* in the FreeKiosk settings, or:

```bash
adb shell dpm remove-active-admin com.freekiosk/.DeviceAdminReceiver
```
