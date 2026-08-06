# Copyright (c) 2026, Adomio · Yücel & Tirgil GbR and contributors
# For license information, please see license.txt

import frappe


def before_tests():
	"""Bootstrap a bare test site (CI): the ERPNext setup wizard has never run
	there, so Company creation would fail on missing fixtures (warehouse types,
	fiscal year, ...). frappe only pulls before_tests hooks from the app under
	test — so timeclock wires this itself and delegates to HRMS, which completes
	the wizard and seeds HR defaults. On an already set-up site (local dev
	bench) this is a deliberate no-op to leave real data untouched."""
	if frappe.get_all("Company", limit=1):
		return

	from hrms.tests.test_utils import before_tests as hrms_before_tests

	hrms_before_tests()
