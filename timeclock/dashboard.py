import frappe
from frappe import _
from frappe.utils import getdate, nowdate

from timeclock.permissions import has_app_permission

# Newest checkin per timeclock-enabled active employee (window over all logs, so a
# forgotten OUT from yesterday is distinguishable from someone present today).
LAST_LOG_SQL = """
	SELECT e.name, e.employee_name, c.log_type, c.time, c.device_id
	FROM `tabEmployee` e
	JOIN (
		SELECT employee, log_type, time, device_id,
			ROW_NUMBER() OVER (PARTITION BY employee ORDER BY time DESC) AS rn
		FROM `tabEmployee Checkin`
	) c ON c.employee = e.name AND c.rn = 1
	WHERE e.status = 'Active' AND e.timeclock_enabled = 1
"""


def _check_admin():
	if not has_app_permission():
		frappe.throw(_("Not permitted"), frappe.PermissionError)


def _last_logs():
	return frappe.db.sql(LAST_LOG_SQL, as_dict=True)


@frappe.whitelist()
def present_now(filters=None):
	"""Number card: employees whose newest log is an IN from today."""
	_check_admin()
	today = getdate()
	return sum(1 for row in _last_logs() if row.log_type == "IN" and getdate(row.time) == today)


@frappe.whitelist()
def checkins_today(filters=None):
	"""Number card: raw punches today (IN + OUT)."""
	_check_admin()
	return frappe.db.count("Employee Checkin", {"time": [">=", nowdate()]})


@frappe.whitelist()
def missing_out(filters=None):
	"""Number card: newest log is an IN from a previous day — forgotten check-outs
	that need a manual correction before auto attendance can be trusted."""
	_check_admin()
	today = getdate()
	return sum(1 for row in _last_logs() if row.log_type == "IN" and getdate(row.time) < today)


@frappe.whitelist()
def absent_today(filters=None):
	"""Number card: today's Attendance records marked Absent."""
	_check_admin()
	return frappe.db.count(
		"Attendance",
		{"attendance_date": nowdate(), "status": "Absent", "docstatus": ["<", 2]},
	)


@frappe.whitelist()
def get_present_board(filters=None):
	"""'Who's in' board for the workspace custom block: name, in since, device."""
	_check_admin()
	today = getdate()
	rows = [r for r in _last_logs() if r.log_type == "IN" and getdate(r.time) == today]
	rows.sort(key=lambda r: r.time)
	return [
		{
			"employee_name": r.employee_name,
			"since": r.time.strftime("%H:%M"),
			"device": r.device_id or "",
		}
		for r in rows
	]
