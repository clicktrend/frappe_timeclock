import hmac
import uuid

import frappe
from frappe import _
from frappe.utils import now_datetime, time_diff_in_seconds
from frappe.utils.password import get_decrypted_password

from timeclock.install import KIOSK_ROLE

MAX_PIN_ATTEMPTS = 5
LOCKOUT_SECONDS = 60
UNDO_WINDOW_SECONDS = 30


def _check_kiosk_access():
	roles = frappe.get_roles()
	if KIOSK_ROLE not in roles and "System Manager" not in roles:
		frappe.throw(_("Not permitted"), frappe.PermissionError)


@frappe.whitelist()
def get_kiosk_config():
	"""Kiosk behaviour flags from Timeclock Settings (single)."""
	_check_kiosk_access()
	settings = frappe.get_cached_doc("Timeclock Settings")
	return {"show_camera_preview": bool(settings.show_camera_preview)}


@frappe.whitelist()
def get_kiosk_employees():
	"""Employees shown on the kiosk grid, with a suggested direction from their last log."""
	_check_kiosk_access()

	employees = frappe.get_all(
		"Employee",
		filters={"status": "Active", "timeclock_enabled": 1},
		fields=["name", "employee_name", "image"],
		order_by="employee_name asc",
	)
	if not employees:
		return []

	last_logs = frappe.db.sql(
		"""
		SELECT employee, log_type, time FROM (
			SELECT employee, log_type, time,
				ROW_NUMBER() OVER (PARTITION BY employee ORDER BY time DESC) AS rn
			FROM `tabEmployee Checkin`
			WHERE employee IN %(employees)s
		) ranked
		WHERE rn = 1
		""",
		{"employees": [e.name for e in employees]},
		as_dict=True,
	)
	by_employee = {row.employee: row for row in last_logs}

	for emp in employees:
		last = by_employee.get(emp.name)
		emp["last_log_type"] = last.log_type if last else None
		emp["last_time"] = last.time if last else None
		emp["suggested_log_type"] = "OUT" if last and last.log_type == "IN" else "IN"

	return employees


@frappe.whitelist()
def punch(employee: str, log_type: str, pin: str, device_id: str | None = None):
	"""Validate the employee's PIN server-side and create an Employee Checkin."""
	_check_kiosk_access()

	if log_type not in ("IN", "OUT"):
		frappe.throw(_("Invalid log type"))

	emp = frappe.db.get_value(
		"Employee",
		employee,
		["name", "employee_name", "status", "timeclock_enabled"],
		as_dict=True,
	)
	if not emp or emp.status != "Active" or not emp.timeclock_enabled:
		frappe.throw(_("Employee is not enabled for the time clock"))

	cache_key = f"timeclock_pin_fail:{employee}"
	fails = frappe.cache.get_value(cache_key) or 0
	if int(fails) >= MAX_PIN_ATTEMPTS:
		frappe.throw(_("Too many wrong attempts. Please wait a minute and try again."))

	stored_pin = get_decrypted_password("Employee", employee, "timeclock_pin", raise_exception=False)
	if not stored_pin:
		frappe.throw(_("No PIN is set for this employee. Please contact HR."))

	if not hmac.compare_digest(str(stored_pin), str(pin)):
		frappe.cache.set_value(cache_key, int(fails) + 1, expires_in_sec=LOCKOUT_SECONDS)
		frappe.throw(_("Wrong PIN"))

	frappe.cache.delete_value(cache_key)
	return _insert_checkin(emp, log_type, device_id)


@frappe.whitelist()
def punch_badge(badge_id: str, device_id: str | None = None):
	"""QR badge scan: resolve the badge, toggle the direction from the last log
	and create an Employee Checkin. The badge is a possession factor (random
	UUID), so no PIN is required — the PIN path stays available in parallel."""
	_check_kiosk_access()

	if not badge_id:
		frappe.throw(_("Missing badge"))

	cache_key = f"timeclock_badge_fail:{frappe.session.user}:{device_id or 'kiosk'}"
	fails = frappe.cache.get_value(cache_key) or 0
	if int(fails) >= MAX_PIN_ATTEMPTS:
		frappe.throw(_("Too many unknown badges. Please wait a minute and try again."))

	emp = frappe.db.get_value(
		"Employee",
		{"timeclock_badge_id": badge_id.strip()},
		["name", "employee_name", "status", "timeclock_enabled"],
		as_dict=True,
	)
	if not emp or emp.status != "Active" or not emp.timeclock_enabled:
		frappe.cache.set_value(cache_key, int(fails) + 1, expires_in_sec=LOCKOUT_SECONDS)
		frappe.throw(_("Unknown badge"))

	frappe.cache.delete_value(cache_key)

	last_log_type = frappe.db.get_value(
		"Employee Checkin", {"employee": emp.name}, "log_type", order_by="time desc"
	)
	log_type = "OUT" if last_log_type == "IN" else "IN"
	return _insert_checkin(emp, log_type, device_id)


@frappe.whitelist()
def undo_punch(checkin: str, device_id: str | None = None):
	"""Undo a punch right after it happened (badge scans have no confirmation step).
	Only the same kiosk device may undo, and only within the undo window."""
	_check_kiosk_access()

	doc = frappe.get_doc("Employee Checkin", checkin)
	if (doc.device_id or "kiosk") != (device_id or "kiosk"):
		frappe.throw(_("Not permitted"), frappe.PermissionError)
	if time_diff_in_seconds(now_datetime(), doc.creation) > UNDO_WINDOW_SECONDS:
		frappe.throw(_("Undo window has expired"))

	frappe.delete_doc("Employee Checkin", checkin, ignore_permissions=True)
	return {"undone": checkin}


@frappe.whitelist()
def generate_badge(employee: str):
	"""HR action on the Employee form: (re)issue the badge UUID. Regenerating
	invalidates the previous badge immediately (lost card scenario)."""
	if not frappe.has_permission("Employee", "write", doc=employee):
		frappe.throw(_("Not permitted"), frappe.PermissionError)

	badge_id = uuid.uuid4().hex
	frappe.db.set_value("Employee", employee, "timeclock_badge_id", badge_id)
	return badge_id


def _insert_checkin(emp, log_type: str, device_id: str | None):
	checkin = frappe.get_doc(
		{
			"doctype": "Employee Checkin",
			"employee": emp.name,
			"log_type": log_type,
			"time": now_datetime(),
			"device_id": device_id,
		}
	)
	checkin.insert(ignore_permissions=True)

	return {
		"name": checkin.name,
		"employee": emp.name,
		"employee_name": emp.employee_name,
		"log_type": log_type,
		"time": checkin.time,
		"undo_seconds": UNDO_WINDOW_SECONDS,
	}
