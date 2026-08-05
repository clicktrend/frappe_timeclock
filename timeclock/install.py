import json

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

KIOSK_ROLE = "Timeclock Kiosk"
WORKSPACE = "Timeclock"
WORKSPACE_ROLES = ["System Manager", "HR Manager"]

# App-owned custom fields on Employee. Created on install AND on migrate so they
# survive site migrations without shipping fixtures (idempotent by fieldname).
# They live in their own "Time Clock" tab (Tab Break created dynamically in
# setup(), appended after the form's last field), reachable via URL anchor
# #timeclock_tab — frappe activates the tab whose fieldname matches the hash.
CUSTOM_FIELDS = {
	"Employee": [
		{
			"fieldname": "timeclock_section",
			"fieldtype": "Section Break",
			"insert_after": "timeclock_tab",
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
		{
			"fieldname": "timeclock_badge_qr",
			"fieldtype": "HTML",
			"insert_after": "timeclock_badge_id",
			"depends_on": "eval:doc.timeclock_badge_id",
		},
	]
}


def after_install():
	setup()


def after_migrate():
	setup()


def setup():
	_ensure_employee_tab()
	create_custom_fields(CUSTOM_FIELDS, ignore_validate=True)
	_fix_field_order()
	_ensure_kiosk_role()
	_ensure_badge_print_format()
	_ensure_number_cards()
	_ensure_dashboard_chart()
	_ensure_whoisin_block()
	_ensure_workspace()
	_ensure_app_tile()
	_seed_settings_defaults()


# Check fields on a never-saved Single read as 0, silently ignoring the field's
# declared default — seed defaults that differ from 0 once, explicitly.
SETTINGS_DEFAULTS = {"play_sounds": 1}


def _seed_settings_defaults():
	for field, value in SETTINGS_DEFAULTS.items():
		stored = frappe.db.get_value(
			"Singles", {"doctype": "Timeclock Settings", "field": field}, "value", order_by=None
		)
		if stored is None:
			frappe.db.set_value("Timeclock Settings", None, field, value)
	frappe.clear_document_cache("Timeclock Settings", "Timeclock Settings")


def _ensure_employee_tab():
	"""Own 'Time Clock' tab on the Employee form, appended after the last existing
	field. Created once; the anchor is computed dynamically because the last field
	differs per installed apps."""
	if frappe.db.exists("Custom Field", {"dt": "Employee", "fieldname": "timeclock_tab"}):
		return

	own_fields = {field["fieldname"] for field in CUSTOM_FIELDS["Employee"]}
	last_field = [f.fieldname for f in frappe.get_meta("Employee").fields if f.fieldname not in own_fields][
		-1
	]
	create_custom_fields(
		{
			"Employee": [
				{
					"fieldname": "timeclock_tab",
					"fieldtype": "Tab Break",
					"label": "Time Clock",
					"insert_after": last_field,
				}
			]
		},
		ignore_validate=True,
	)


def _fix_field_order():
	"""Upgrade path: releases before the Tab Break placed the section after
	attendance_device_id as a collapsible 'Time Clock' section — move it under the
	tab, always expanded, headerless (create_custom_fields does not touch existing
	fields)."""
	section = frappe.db.get_value(
		"Custom Field",
		{"dt": "Employee", "fieldname": "timeclock_section"},
		["name", "insert_after", "label", "collapsible"],
		as_dict=True,
	)
	if not section:
		return

	updates = {}
	if section.insert_after != "timeclock_tab":
		updates["insert_after"] = "timeclock_tab"
	if section.collapsible:
		updates["collapsible"] = 0
	if section.label:
		updates["label"] = ""
	if updates:
		frappe.db.set_value("Custom Field", section.name, updates)
		frappe.clear_cache(doctype="Employee")


def _ensure_kiosk_role():
	if not frappe.db.exists("Role", KIOSK_ROLE):
		frappe.get_doc(
			{
				"doctype": "Role",
				"role_name": KIOSK_ROLE,
				"desk_access": 0,
			}
		).insert(ignore_permissions=True)


# Number Card names itself after its label (autoname) — the label IS the identity.
NUMBER_CARDS = [
	{"label": "Jetzt anwesend", "method": "timeclock.dashboard.present_now"},
	{"label": "Heute gestempelt", "method": "timeclock.dashboard.checkins_today"},
	{"label": "Fehlende OUT-Stempel", "method": "timeclock.dashboard.missing_out"},
	{"label": "Abwesend heute", "method": "timeclock.dashboard.absent_today"},
]

DASHBOARD_CHART = "Timeclock Arbeitsstunden"
WHOISIN_BLOCK = "Timeclock Who's In"

WHOISIN_HTML = """<div class="tc-whoisin">
	<div class="tc-title">Wer ist da</div>
	<div class="tc-board"><div class="tc-empty">Lade …</div></div>
</div>"""

WHOISIN_SCRIPT = """frappe.call({ method: "timeclock.dashboard.get_present_board" }).then((r) => {
	const rows = r.message || [];
	const board = root_element.querySelector(".tc-board");
	if (!rows.length) {
		board.innerHTML = "<div class='tc-empty'>Niemand eingestempelt</div>";
		return;
	}
	board.innerHTML = rows
		.map(
			(x) =>
				`<div class="tc-row"><span class="tc-dot"></span><span class="tc-name">${frappe.utils.escape_html(
					x.employee_name
				)}</span><span class="tc-meta">seit ${x.since}${
					x.device ? " · " + frappe.utils.escape_html(x.device) : ""
				}</span></div>`
		)
		.join("");
});"""

WHOISIN_STYLE = """.tc-whoisin { padding: 8px 4px; }
.tc-title { font-size: 15px; font-weight: 600; margin-bottom: 10px; }
.tc-board { display: flex; flex-direction: column; gap: 6px; }
.tc-row { display: flex; align-items: center; gap: 8px; padding: 6px 10px; background: var(--bg-color, #f8f8f8); border-radius: 8px; }
.tc-dot { width: 8px; height: 8px; border-radius: 50%; background: #22c55e; flex-shrink: 0; }
.tc-name { font-weight: 500; }
.tc-meta { color: var(--text-muted, #888); font-size: 12px; margin-left: auto; }
.tc-empty { color: var(--text-muted, #888); padding: 4px 2px; }"""


def _ensure_number_cards():
	for card in NUMBER_CARDS:
		if frappe.db.exists("Number Card", card["label"]):
			frappe.db.set_value("Number Card", card["label"], "method", card["method"])
			continue
		frappe.get_doc(
			{
				"doctype": "Number Card",
				"label": card["label"],
				"type": "Custom",
				"method": card["method"],
				"is_public": 1,
				"module": "Timeclock",
			}
		).insert(ignore_permissions=True)


def _ensure_dashboard_chart():
	if frappe.db.exists("Dashboard Chart", DASHBOARD_CHART):
		return
	frappe.get_doc(
		{
			"doctype": "Dashboard Chart",
			"chart_name": DASHBOARD_CHART,
			"chart_type": "Sum",
			"document_type": "Attendance",
			"based_on": "attendance_date",
			"value_based_on": "working_hours",
			"timespan": "Last Month",
			"time_interval": "Daily",
			"timeseries": 1,
			"type": "Bar",
			"filters_json": "[]",
			"is_public": 1,
			"module": "Timeclock",
		}
	).insert(ignore_permissions=True)


def _ensure_whoisin_block():
	if frappe.db.exists("Custom HTML Block", WHOISIN_BLOCK):
		frappe.db.set_value(
			"Custom HTML Block",
			WHOISIN_BLOCK,
			{"html": WHOISIN_HTML, "script": WHOISIN_SCRIPT, "style": WHOISIN_STYLE},
			update_modified=False,
		)
		return
	doc = frappe.new_doc("Custom HTML Block")
	doc.name = WHOISIN_BLOCK
	doc.update({"html": WHOISIN_HTML, "script": WHOISIN_SCRIPT, "style": WHOISIN_STYLE})
	doc.insert(ignore_permissions=True)


WORKSPACE_SHORTCUTS = [
	{"label": "Timeclock Settings", "link_to": "Timeclock Settings", "type": "DocType"},
	{
		"label": "Employees",
		"link_to": "Employee",
		"type": "DocType",
		"doc_view": "List",
		# timeclock context marker: the employee list JS appends #timeclock_tab to
		# row links while this filter is active, landing directly on our tab
		"stats_filter": json.dumps({"timeclock_enabled": 1}),
	},
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
	for i, card in enumerate(NUMBER_CARDS):
		content.append(
			{
				"id": f"tcCard{i}",
				"type": "number_card",
				"data": {"number_card_name": card["label"], "col": 3},
			}
		)
	content.append(
		{
			"id": "tcWhoIsIn",
			"type": "custom_block",
			"data": {"custom_block_name": WHOISIN_BLOCK, "col": 12},
		}
	)
	content.append({"id": "tcChart", "type": "chart", "data": {"chart_name": DASHBOARD_CHART, "col": 12}})
	content.append({"id": "tcSpacer", "type": "spacer", "data": {"col": 12}})
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
	doc.set("number_cards", [])
	for card in NUMBER_CARDS:
		doc.append("number_cards", {"number_card_name": card["label"], "label": card["label"]})
	doc.set("custom_blocks", [])
	doc.append("custom_blocks", {"custom_block_name": WHOISIN_BLOCK, "label": WHOISIN_BLOCK})
	doc.set("charts", [])
	doc.append("charts", {"chart_name": DASHBOARD_CHART, "label": DASHBOARD_CHART})
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
