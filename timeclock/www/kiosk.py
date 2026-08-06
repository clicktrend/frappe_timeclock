import hmac

import frappe

no_cache = 1


def get_context(context):
	if frappe.session.user == "Guest":
		if not _try_token_login():
			frappe.local.flags.redirect_location = "/login?redirect-to=/kiosk"
			raise frappe.Redirect

	context.csrf_token = frappe.sessions.get_csrf_token()
	return context


def _try_token_login() -> bool:
	"""Kiosk device auto-login: /kiosk?token=<secret> signs in the configured kiosk
	user, so wall-mounted terminals survive reboots and session expiry without
	anyone typing credentials. The token lives in Timeclock Settings (revocable at
	any time) and only ever logs into a locked-down kiosk account — users with
	System Manager or without the Timeclock Kiosk role are refused."""
	token = frappe.form_dict.get("token")
	if not token:
		return False

	settings = frappe.get_cached_doc("Timeclock Settings")
	user = settings.get("kiosk_autologin_user")
	stored = settings.get("kiosk_autologin_token")
	if not (user and stored and len(str(stored)) >= 20):
		return False
	if not hmac.compare_digest(str(token), str(stored)):
		return False

	roles = frappe.get_roles(user)
	if "System Manager" in roles or "Timeclock Kiosk" not in roles:
		return False

	frappe.local.login_manager.login_as(user)
	return True
