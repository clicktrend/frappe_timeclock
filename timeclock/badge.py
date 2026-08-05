import io

import frappe
import pyqrcode


def timeclock_badge_qr_svg(employee: str) -> str:
	"""Inline SVG of the employee's badge QR — used by the 'Timeclock Badge' print format
	(registered as a Jinja method in hooks.py). Renders server-side, nothing leaves the site."""
	badge_id = frappe.db.get_value("Employee", employee, "timeclock_badge_id")
	if not badge_id:
		return ""
	qr = pyqrcode.create(badge_id)
	buf = io.BytesIO()
	qr.svg(buf, scale=4, module_color="#000000", background="#ffffff", xmldecl=False)
	return buf.getvalue().decode()
