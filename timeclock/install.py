import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

KIOSK_ROLE = "Timeclock Kiosk"

# App-owned custom fields on Employee. Created on install AND on migrate so they
# survive site migrations without shipping fixtures (idempotent by fieldname).
CUSTOM_FIELDS = {
	"Employee": [
		{
			"fieldname": "timeclock_section",
			"fieldtype": "Section Break",
			"label": "Time Clock",
			"insert_after": "attendance_device_id",
			"collapsible": 1,
		},
		{
			"fieldname": "timeclock_enabled",
			"fieldtype": "Check",
			"label": "Time Clock Enabled",
			"insert_after": "timeclock_section",
		},
		{
			"fieldname": "timeclock_pin",
			"fieldtype": "Password",
			"label": "Time Clock PIN",
			"insert_after": "timeclock_enabled",
			"depends_on": "timeclock_enabled",
		},
		{
			"fieldname": "timeclock_badge_id",
			"fieldtype": "Data",
			"label": "Time Clock Badge ID",
			"insert_after": "timeclock_pin",
			"depends_on": "timeclock_enabled",
			"read_only": 1,
			"unique": 1,
			"no_copy": 1,
		},
	]
}


def after_install():
	setup()


def after_migrate():
	setup()


def setup():
	create_custom_fields(CUSTOM_FIELDS, ignore_validate=True)
	_ensure_kiosk_role()
	_ensure_badge_print_format()


def _ensure_kiosk_role():
	if not frappe.db.exists("Role", KIOSK_ROLE):
		frappe.get_doc(
			{
				"doctype": "Role",
				"role_name": KIOSK_ROLE,
				"desk_access": 0,
			}
		).insert(ignore_permissions=True)


def _ensure_badge_print_format():
	"""Create/update the 'Timeclock Badge' print format from the app's template file
	so the HTML source of truth stays in git (updated on every migrate)."""
	html = frappe.read_file(frappe.get_app_path("timeclock", "templates", "badge_print.html"))
	if frappe.db.exists("Print Format", "Timeclock Badge"):
		frappe.db.set_value("Print Format", "Timeclock Badge", "html", html, update_modified=False)
	else:
		frappe.get_doc(
			{
				"doctype": "Print Format",
				"name": "Timeclock Badge",
				"doc_type": "Employee",
				"module": "Timeclock",
				"custom_format": 1,
				"print_format_type": "Jinja",
				"html": html,
			}
		).insert(ignore_permissions=True)
