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
	]
}


def after_install():
	setup()


def after_migrate():
	setup()


def setup():
	create_custom_fields(CUSTOM_FIELDS, ignore_validate=True)
	_ensure_kiosk_role()


def _ensure_kiosk_role():
	if not frappe.db.exists("Role", KIOSK_ROLE):
		frappe.get_doc(
			{
				"doctype": "Role",
				"role_name": KIOSK_ROLE,
				"desk_access": 0,
			}
		).insert(ignore_permissions=True)
