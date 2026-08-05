import frappe

# Who counts as a timeclock admin: sees the app tile and the Timeclock workspace.
# Regular employees (and the kiosk user) do not.
ADMIN_ROLES = {"System Manager", "HR Manager"}


def has_app_permission() -> bool:
	return bool(ADMIN_ROLES & set(frappe.get_roles()))
