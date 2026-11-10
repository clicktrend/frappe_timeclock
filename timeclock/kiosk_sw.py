# Copyright (c) 2026, Adomio · Yücel & Tirgil GbR and contributors
# For license information, please see license.txt

"""Serves the kiosk service worker at /kiosk-sw.js.

A service worker can only control pages at or below its own path, and Frappe
neither serves .js from www/ nor lets /assets/ widen the scope (that needs a
Service-Worker-Allowed header the static file server will not send). A page
renderer at the site root is the smallest way to get both: the right MIME type
and a scope that covers /kiosk.
"""

import frappe
from frappe.website.page_renderers.base_renderer import BaseRenderer
from werkzeug.wrappers import Response

PATH = "kiosk-sw.js"
# get_app_path scrubs every path segment ("-" -> "_"), so the source file must not
# carry a dash — with one it silently resolves to a missing file
SOURCE = ("templates", "kiosk_sw.js")


class KioskServiceWorker(BaseRenderer):
	def can_render(self):
		return self.path == PATH

	def render(self):
		source = frappe.read_file(frappe.get_app_path("timeclock", *SOURCE), raise_not_found=True)
		response = Response(source, mimetype="application/javascript")
		# the browser re-checks the worker on every page load — never serve a stale one
		response.headers["Cache-Control"] = "no-cache"
		return response
