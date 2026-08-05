import frappe

no_cache = 1


def get_context(context):
	if frappe.session.user == "Guest":
		frappe.local.flags.redirect_location = "/login?redirect-to=/kiosk"
		raise frappe.Redirect

	context.csrf_token = frappe.sessions.get_csrf_token()
	return context
