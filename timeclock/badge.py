import io

import frappe
import pyqrcode


def timeclock_badge_qr_svg(employee: str) -> str:
	"""Inline SVG of the employee's badge QR — used by the 'Timeclock Badge' print format
	(registered as a Jinja method in hooks.py). Renders server-side, nothing leaves the site."""
	badge_id = frappe.db.get_value("Employee", employee, "timeclock_badge_id")
	if not badge_id:
		return ""
	# Error correction "L": a 32-char badge fits in 25x25 modules instead of 33x33
	# (pyqrcode default "H") — larger modules on the same print size scan noticeably
	# faster and tolerate more blur on fixed-focus tablet cameras. Redundancy is not
	# needed: badges are printed flat, never damaged like outdoor labels.
	qr = pyqrcode.create(badge_id, error="l")
	buf = io.BytesIO()
	qr.svg(buf, scale=4, module_color="#000000", background="#ffffff", xmldecl=False)
	return buf.getvalue().decode()
