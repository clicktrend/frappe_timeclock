import json

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

KIOSK_ROLE = "Timeclock Kiosk"
WORKSPACE = "Timeclock"
WORKSPACE_ROLES = ["System Manager", "HR Manager"]

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
	_ensure_workspace()
	_ensure_app_tile()


def _ensure_kiosk_role():
	if not frappe.db.exists("Role", KIOSK_ROLE):
		frappe.get_doc(
			{
				"doctype": "Role",
				"role_name": KIOSK_ROLE,
				"desk_access": 0,
			}
		).insert(ignore_permissions=True)


WORKSPACE_SHORTCUTS = [
	{"label": "Timeclock Settings", "link_to": "Timeclock Settings", "type": "DocType"},
	{"label": "Employees", "link_to": "Employee", "type": "DocType", "doc_view": "List"},
	{"label": "Checkins", "link_to": "Employee Checkin", "type": "DocType", "doc_view": "List"},
	{"label": "Attendance", "link_to": "Attendance", "type": "DocType", "doc_view": "List"},
]


def _ensure_workspace():
	"""Admin workspace (settings + employee/PIN/badge management), restricted via
	workspace roles — regular employees never see it. Idempotent on migrate."""
	content = [
		{
			"id": "tcHeader",
			"type": "header",
			"data": {"text": "<span class='h4'><b>Timeclock</b></span>", "col": 12},
		}
	]
	for i, shortcut in enumerate(WORKSPACE_SHORTCUTS):
		content.append(
			{
				"id": f"tcShortcut{i}",
				"type": "shortcut",
				"data": {"shortcut_name": shortcut["label"], "col": 3},
			}
		)

	if frappe.db.exists("Workspace", WORKSPACE):
		doc = frappe.get_doc("Workspace", WORKSPACE)
	else:
		doc = frappe.new_doc("Workspace")
		doc.name = WORKSPACE

	doc.update(
		{
			"title": WORKSPACE,
			"label": WORKSPACE,
			"module": "Timeclock",
			"public": 1,
			"icon": "time",
			"content": json.dumps(content),
		}
	)
	doc.set("shortcuts", [])
	for shortcut in WORKSPACE_SHORTCUTS:
		doc.append("shortcuts", shortcut)
	doc.set("roles", [])
	for role in WORKSPACE_ROLES:
		doc.append("roles", {"role": role})

	doc.flags.ignore_permissions = True
	doc.flags.ignore_links = True
	if doc.is_new():
		doc.insert(ignore_permissions=True)
	else:
		doc.save()


def _ensure_app_tile():
	"""Frappe v16 creates /desk app tiles only in after_app_install, so re-ensure the
	Timeclock tile on every migrate (pattern proven in the adomio app). The workspace
	auto-shortcut may claim the doc name 'Timeclock' (Desktop Icon name == label) and
	collide with the app tile — drop it first."""
	from frappe.desk.doctype.desktop_icon.desktop_icon import create_desktop_icons_from_installed_apps

	stale_icon_type = frappe.db.get_value("Desktop Icon", WORKSPACE, "icon_type")
	if stale_icon_type and stale_icon_type != "App":
		frappe.delete_doc("Desktop Icon", WORKSPACE, ignore_permissions=True)

	create_desktop_icons_from_installed_apps()

	frappe.cache.delete_key("desktop_icons")
	frappe.cache.delete_key("bootinfo")


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
