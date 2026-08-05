import frappe
from frappe.utils import now_datetime


def update_last_sync_of_checkin():
	"""The kiosk writes Employee Checkin in realtime, but HRMS auto attendance only
	processes logs up to Shift Type.last_sync_of_checkin (normally advanced by the
	biometric sync tool). Keep it current for all auto-attendance shifts."""
	for name in frappe.get_all("Shift Type", filters={"enable_auto_attendance": 1}, pluck="name"):
		frappe.db.set_value("Shift Type", name, "last_sync_of_checkin", now_datetime(), update_modified=False)
