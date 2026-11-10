# Copyright (c) 2026, Adomio · Yücel & Tirgil GbR and contributors
# For license information, please see license.txt

"""Offline punches and the kiosk device registry.

An online punch gets its timestamp from the server. A punch taken while the kiosk
could not reach the server carries a time the *device* claims — so it must not be
written to Employee Checkin unchecked. Every offline punch lands in Timeclock
Queued Punch first (claimed time, receive time, clock offset), is verified there
(PIN or badge, plausible time) and only then becomes a regular Employee Checkin.
Everything that does not pass stays in quarantine for HR.

The device never holds a secret to verify a punch: PIN and badge travel inside the
queued punch and are checked here, at sync time.
"""

import hashlib
import hmac
import json
import re
from datetime import timedelta

import frappe
from frappe import _
from frappe.utils import cint, get_datetime, get_time, getdate, now_datetime
from frappe.utils.password import get_decrypted_password

# Status flips to Offline after this much silence (heartbeat runs every 30 s).
ONLINE_GRACE_SECONDS = 120
# Tablet clocks drift a little even after correction — tolerate it.
FUTURE_TOLERANCE_SECONDS = 120
# Same employee, same direction, this close together: probably the same punch twice.
DUPLICATE_WINDOW_SECONDS = 120
MAX_BATCH = 100
DEVICE_ID_PATTERN = re.compile(r"^[\w.\-]{1,64}$")


def badge_hash(badge_id: str) -> str:
	return hashlib.sha256(badge_id.strip().encode()).hexdigest()


def current_kiosk_build() -> str | None:
	"""Hash of the kiosk bundle the server currently ships, read from the built page.
	The kiosk derives the same value from its own script URL, so both sides agree
	without any build step injecting a version."""
	try:
		html = frappe.read_file(frappe.get_app_path("timeclock", "www", "kiosk.html")) or ""
	except Exception:
		return None
	match = re.search(r"/assets/index-([\w-]+)\.js", html)
	return match.group(1) if match else None


def clean_device_id(device_id: str | None) -> str:
	device_id = (device_id or "kiosk").strip()
	if not DEVICE_ID_PATTERN.match(device_id):
		frappe.throw(_("Invalid device ID"))
	return device_id


# ---------------------------------------------------------------------------
# device registry
# ---------------------------------------------------------------------------


def record_heartbeat(device_id: str, version: str | None, build: str | None, pending: int) -> dict:
	device_id = clean_device_id(device_id)
	now = now_datetime()
	current = current_kiosk_build()
	outdated = bool(current and build and build != current)
	values = {
		"status": "Online",
		"last_seen": now,
		"offline_since": None,
		"app_version": f"{version or '?'} ({build or '?'})",
		"outdated": 1 if outdated else 0,
		"pending_punches": max(cint(pending), 0),
		"user_agent": _user_agent(),
		"last_ip": getattr(frappe.local, "request_ip", None),
	}

	if frappe.db.exists("Timeclock Device", device_id):
		previous = frappe.db.get_value(
			"Timeclock Device", device_id, ["status", "alert_sent", "offline_since", "label"], as_dict=True
		)
		if previous.alert_sent:
			values["alert_sent"] = 0
			_send_recovery(device_id, previous.label, previous.offline_since, now)
		# heartbeats arrive every 30 s — keep them out of `modified` and the version trail
		frappe.db.set_value("Timeclock Device", device_id, values, update_modified=False)
	else:
		doc = frappe.new_doc("Timeclock Device")
		doc.device_id = device_id
		doc.update(values)
		doc.insert(ignore_permissions=True)

	return {"server_time": str(now), "reload": outdated, "build": current}


def _user_agent() -> str:
	request = getattr(frappe.local, "request", None)
	return (request.headers.get("User-Agent") or "")[:500] if request else ""


def ensure_device(device_id: str):
	if not frappe.db.exists("Timeclock Device", device_id):
		doc = frappe.new_doc("Timeclock Device")
		doc.device_id = device_id
		doc.status = "Online"
		doc.last_seen = now_datetime()
		doc.insert(ignore_permissions=True)


def check_devices():
	"""Scheduler (every minute): mark silent devices offline, alert once per outage."""
	now = now_datetime()
	settings = frappe.get_cached_doc("Timeclock Settings")
	alert_minutes = cint(settings.device_alert_minutes)
	recipients = _recipients(settings)

	for device in frappe.get_all(
		"Timeclock Device",
		fields=["name", "label", "status", "last_seen", "offline_since", "alert_sent"],
	):
		if not device.last_seen:
			continue
		silent = (now - get_datetime(device.last_seen)).total_seconds()
		if device.status == "Online" and silent > ONLINE_GRACE_SECONDS:
			frappe.db.set_value(
				"Timeclock Device",
				device.name,
				{"status": "Offline", "offline_since": device.last_seen},
				update_modified=False,
			)
			device.status = "Offline"
			device.offline_since = device.last_seen

		if (
			device.status == "Offline"
			and not device.alert_sent
			and alert_minutes > 0
			and recipients
			and silent >= alert_minutes * 60
			and _in_alert_window(settings, now)
		):
			_send_alert(device, recipients)
			frappe.db.set_value("Timeclock Device", device.name, "alert_sent", 1, update_modified=False)


def _in_alert_window(settings, now) -> bool:
	if now.weekday() >= 5 and not settings.device_alert_weekends:
		return False
	start = get_time(settings.device_alert_from or "00:00:00")
	end = get_time(settings.device_alert_to or "23:59:59")
	return start <= now.time() <= end


def _recipients(settings) -> list[str]:
	raw = settings.get("device_alert_recipients") or ""
	return [line.strip() for line in re.split(r"[\n,;]", raw) if line.strip()]


def _sendmail(**kwargs):
	"""Alerts are a side channel: a missing outgoing email account must never break
	a heartbeat, a sync or the scheduler tick."""
	try:
		frappe.sendmail(**kwargs)
	except Exception:
		frappe.log_error(title="Timeclock: could not send alert email")


def _device_title(name, label) -> str:
	return f"{label} ({name})" if label else name


def _send_alert(device, recipients):
	title = _device_title(device.name, device.label)
	_sendmail(
		recipients=recipients,
		subject=_("Time clock offline: {0}").format(title),
		message=_(
			"The time clock {0} has not reported since {1}. Punches taken there now are stored on the "
			"tablet and booked once it is back online — unless it is switched off or has no power."
		).format(frappe.bold(title), device.last_seen),
	)


def _send_recovery(device_id, label, offline_since, now):
	recipients = _recipients(frappe.get_cached_doc("Timeclock Settings"))
	if not recipients:
		return
	title = _device_title(device_id, label)
	_sendmail(
		recipients=recipients,
		subject=_("Time clock back online: {0}").format(title),
		message=_("The time clock {0} is reachable again (offline since {1}, back at {2}).").format(
			frappe.bold(title), offline_since or "?", now
		),
	)


# ---------------------------------------------------------------------------
# offline punches
# ---------------------------------------------------------------------------


def sync_punches(device_id: str, punches) -> list[dict]:
	if isinstance(punches, str):
		punches = json.loads(punches)
	if not isinstance(punches, list):
		frappe.throw(_("Invalid punch list"))
	if len(punches) > MAX_BATCH:
		frappe.throw(_("Too many punches in one request"))

	device_id = clean_device_id(device_id)
	ensure_device(device_id)
	settings = frappe.get_cached_doc("Timeclock Settings")
	received = now_datetime()

	# chronological, so a badge toggle sees the punches booked just before it
	punches = sorted(punches, key=lambda p: str(p.get("claimed_time") or ""))
	results, conflicts = [], []
	for punch in punches:
		frappe.db.savepoint("timeclock_punch")
		try:
			doc = _process_punch(punch, device_id, settings, received)
		except Exception:
			frappe.db.rollback(save_point="timeclock_punch")
			frappe.log_error(title="Timeclock: offline punch could not be processed")
			# the kiosk keeps this one and sends it again with the next sync
			results.append({"client_uuid": punch.get("client_uuid"), "status": "Error"})
			continue
		results.append(_result(doc))
		if doc.attendance and doc.get("_new"):
			conflicts.append(doc)

	frappe.db.set_value("Timeclock Device", device_id, {"last_sync": received}, update_modified=False)
	if conflicts:
		_notify_attendance_conflicts(conflicts, settings)
	return results


def _result(doc) -> dict:
	return {
		"client_uuid": doc.client_uuid,
		"status": doc.status,
		"name": doc.name,
		"employee_name": doc.employee_name,
		"log_type": doc.log_type,
		"time": str(doc.claimed_time or ""),
	}


def _process_punch(punch: dict, device_id: str, settings, received):
	client_uuid = str(punch.get("client_uuid") or "").strip()
	if not client_uuid or len(client_uuid) > 64:
		frappe.throw(_("Invalid punch ID"))

	existing = frappe.db.get_value("Timeclock Queued Punch", {"client_uuid": client_uuid}, "name")
	if existing:
		# retry of a sync whose response never reached the kiosk
		return frappe.get_doc("Timeclock Queued Punch", existing)

	doc = frappe.new_doc("Timeclock Queued Punch")
	doc.client_uuid = client_uuid
	doc.device = device_id
	doc.received_time = received
	doc.claimed_time = _parse_time(punch.get("claimed_time"))
	doc.device_time = _parse_time(punch.get("device_time"))
	doc.clock_offset_ms = cint(punch.get("clock_offset_ms"))
	doc.clock_synced_at = _parse_time(punch.get("clock_synced_at"))
	doc.method = "Badge" if punch.get("method") == "Badge" else "PIN"

	emp, reason = _verify_identity(punch, doc)
	if emp:
		doc.employee = emp.name
		doc.employee_name = emp.employee_name
		if not reason and (emp.status != "Active" or not emp.timeclock_enabled):
			reason = _("Employee is not enabled for the time clock")

	if not doc.claimed_time:
		reason = reason or _("The punch has no time")
	elif emp:
		doc.log_type = _log_type(punch, doc, emp)
		if not doc.log_type:
			reason = reason or _("Invalid log type")

	reason = reason or _time_problem(doc, settings, received)
	if not reason and doc.employee:
		reason = _possible_duplicate(doc)

	doc.status = "Quarantine" if reason else "Booked"
	doc.reason = reason
	doc.flags.ignore_permissions = True
	doc.insert()
	doc._new = True

	if doc.status == "Booked":
		_book(doc)
	return doc


def _verify_identity(punch: dict, doc):
	"""Returns (employee row or None, quarantine reason or None)."""
	fields = ["name", "employee_name", "status", "timeclock_enabled"]
	if doc.method == "Badge":
		badge = str(punch.get("badge_id") or "").strip()
		emp = badge and frappe.db.get_value("Employee", {"timeclock_badge_id": badge}, fields, as_dict=True)
		if not emp:
			doc.badge_hash = badge_hash(badge) if badge else None
			return None, _("Unknown badge")
		return emp, None

	employee = str(punch.get("employee") or "")
	emp = employee and frappe.db.get_value("Employee", employee, fields, as_dict=True)
	if not emp:
		return None, _("Unknown employee")
	stored_pin = get_decrypted_password("Employee", emp.name, "timeclock_pin", raise_exception=False)
	if not stored_pin:
		return emp, _("No PIN is set for this employee. Please contact HR.")
	if not hmac.compare_digest(str(stored_pin), str(punch.get("pin") or "")):
		return emp, _("Wrong PIN")
	return emp, None


def _log_type(punch: dict, doc, emp) -> str | None:
	if doc.method == "PIN":
		return punch.get("log_type") if punch.get("log_type") in ("IN", "OUT") else None
	# A badge toggles. The server decides from the last checkin BEFORE the punch time,
	# which also covers punches other kiosks booked in the meantime.
	last = frappe.db.get_value(
		"Employee Checkin",
		{"employee": emp.name, "time": ("<", doc.claimed_time)},
		"log_type",
		order_by="time desc",
	)
	return "OUT" if last == "IN" else "IN"


def _time_problem(doc, settings, received) -> str | None:
	if not doc.clock_synced_at:
		return _("The device clock was never matched with the server")
	claimed = get_datetime(doc.claimed_time)
	if claimed > received + timedelta(seconds=FUTURE_TOLERANCE_SECONDS):
		return _("The punch time lies in the future")
	max_hours = cint(settings.offline_max_age_hours) or 72
	if claimed < received - timedelta(hours=max_hours):
		return _("Older than the allowed offline period ({0} hours)").format(max_hours)
	return None


def _possible_duplicate(doc) -> str | None:
	"""A punch whose answer got lost on the way is queued AND may have reached the
	server — the same direction within a couple of minutes is held for HR."""
	claimed = get_datetime(doc.claimed_time)
	window = timedelta(seconds=DUPLICATE_WINDOW_SECONDS)
	twin = frappe.db.get_value(
		"Employee Checkin",
		{
			"employee": doc.employee,
			"log_type": doc.log_type,
			"time": ("between", [claimed - window, claimed + window]),
		},
		"name",
	)
	return _("Possible duplicate of {0}").format(twin) if twin else None


def _book(doc):
	frappe.db.savepoint("timeclock_checkin")
	try:
		checkin = frappe.get_doc(
			{
				"doctype": "Employee Checkin",
				"employee": doc.employee,
				"log_type": doc.log_type,
				"time": doc.claimed_time,
				"device_id": doc.device,
				"timeclock_queued_punch": doc.name,
			}
		)
		checkin.insert(ignore_permissions=True)
	except frappe.ValidationError as e:
		# e.g. a checkin with the very same timestamp already exists
		frappe.db.rollback(save_point="timeclock_checkin")
		frappe.clear_messages()
		doc.db_set({"status": "Quarantine", "reason": str(e) or _("Could not be booked")})
		return

	values = {"status": "Booked", "checkin": checkin.name}
	attendance = frappe.db.get_value(
		"Attendance",
		{"employee": doc.employee, "attendance_date": getdate(doc.claimed_time), "docstatus": ("<", 2)},
		"name",
	)
	if attendance:
		# Frappe HR skips logs for a day that already has an attendance — HR must look
		values["attendance"] = attendance
	doc.db_set(values)


def book_quarantined(name: str, employee: str | None = None, log_type: str | None = None):
	doc = frappe.get_doc("Timeclock Queued Punch", name)
	doc.check_permission("write")
	if doc.status != "Quarantine":
		frappe.throw(_("Only punches in quarantine can be booked"))
	if employee:
		doc.employee = employee
	if log_type in ("IN", "OUT"):
		doc.log_type = log_type
	if not (doc.employee and doc.log_type and doc.claimed_time):
		frappe.throw(_("Employee, log type and time are required to book this punch"))
	doc.employee_name = frappe.db.get_value("Employee", doc.employee, "employee_name")
	note = _("Booked by {0} after review. Original reason: {1}").format(frappe.session.user, doc.reason)
	doc.db_set(
		{
			"employee": doc.employee,
			"employee_name": doc.employee_name,
			"log_type": doc.log_type,
			"reason": note,
		}
	)
	_book(doc)
	doc.reload()
	return doc.status


def discard_quarantined(name: str):
	doc = frappe.get_doc("Timeclock Queued Punch", name)
	doc.check_permission("write")
	if doc.status != "Quarantine":
		frappe.throw(_("Only punches in quarantine can be discarded"))
	note = _("Discarded by {0}. Original reason: {1}").format(frappe.session.user, doc.reason)
	doc.db_set({"status": "Discarded", "reason": note})
	return doc.status


def _notify_attendance_conflicts(docs, settings):
	recipients = _recipients(settings)
	if not recipients:
		return
	rows = "".join(
		f"<li>{frappe.utils.escape_html(d.employee_name or d.employee)} · {d.log_type} · "
		f"{d.claimed_time} → {d.attendance}</li>"
		for d in docs
	)
	_sendmail(
		recipients=recipients,
		subject=_("Time clock: offline punches on days with attendance already marked"),
		message=_(
			"These offline punches were booked, but their day already had an attendance (for example "
			"'Absent' from the outage). Frappe HR does not re-evaluate such days on its own — please "
			"cancel and re-mark the attendance:"
		)
		+ f"<ul>{rows}</ul>",
	)


def _parse_time(value):
	if not value:
		return None
	try:
		return get_datetime(str(value).replace("T", " ").split(".")[0])
	except Exception:
		return None
