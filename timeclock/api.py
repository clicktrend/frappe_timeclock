import hmac

import frappe
from frappe import _
from frappe.utils import now_datetime
from frappe.utils.password import get_decrypted_password

from timeclock.install import KIOSK_ROLE

MAX_PIN_ATTEMPTS = 5
LOCKOUT_SECONDS = 60


def _check_kiosk_access():
	roles = frappe.get_roles()
	if KIOSK_ROLE not in roles and "System Manager" not in roles:
		frappe.throw(_("Not permitted"), frappe.PermissionError)


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
	}
