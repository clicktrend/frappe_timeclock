# Copyright (c) 2026, Adomio · Yücel & Tirgil GbR and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class TimeclockSettings(Document):
	def validate(self):
		if self.kiosk_autologin_token and len(self.kiosk_autologin_token) < 20:
			frappe.throw(_("Kiosk Auto-Login Token must be at least 20 characters long"))
		if self.kiosk_autologin_user:
			roles = frappe.get_roles(self.kiosk_autologin_user)
			if "System Manager" in roles:
				frappe.throw(_("The kiosk auto-login user must not be a System Manager"))
			if "Timeclock Kiosk" not in roles:
				frappe.throw(_("The kiosk auto-login user needs the Timeclock Kiosk role"))
