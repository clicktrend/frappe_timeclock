# Copyright (c) 2026, Adomio · Yücel & Tirgil GbR and contributors
# For license information, please see license.txt

from datetime import timedelta
from unittest.mock import patch

import frappe
from frappe.utils import add_days, now_datetime, today

try:
	from frappe.tests import IntegrationTestCase
except ImportError:  # frappe < v16
	from frappe.tests.utils import FrappeTestCase as IntegrationTestCase

from timeclock import api

PIN = "1234"


def _get_or_make_company():
	company = frappe.get_all("Company", limit=1)
	if company:
		return company[0].name
	doc = frappe.get_doc(
		{
			"doctype": "Company",
			"company_name": "Timeclock Test Co",
			"abbr": "TTC",
			"default_currency": "EUR",
			"country": "Germany",
		}
	).insert(ignore_permissions=True)
	return doc.name


def _make_employee(first_name, enabled=True, pin=None):
	emp = frappe.get_doc(
		{
			"doctype": "Employee",
			"first_name": first_name,
			"last_name": "TimeclockTest",
			"gender": "Prefer not to say",
			"date_of_birth": "1990-01-01",
			"date_of_joining": add_days(today(), -30),
			"company": _get_or_make_company(),
			"status": "Active",
			"timeclock_enabled": 1 if enabled else 0,
		}
	)
	if pin:
		emp.timeclock_pin = pin
	emp.insert(ignore_permissions=True)
	return emp


class TestTimeclockApi(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")
		cls.emp = _make_employee("Enabled", enabled=True, pin=PIN)
		cls.emp_disabled = _make_employee("Disabled", enabled=False)

	def setUp(self):
		frappe.set_user("Administrator")
		# a previous test may have tripped the lockout counters
		frappe.cache.delete_value(f"timeclock_pin_fail:{self.emp.name}")
		frappe.cache.delete_value("timeclock_badge_fail:Administrator:test-kiosk")

	# HRMS refuses two checkins of one employee with the same timestamp, and the
	# whole test class punches within the same real-world second — so every punch
	# gets its own strictly increasing timestamp via a patched now_datetime.
	_tick = now_datetime()

	@classmethod
	def _next_time(cls):
		cls._tick += timedelta(seconds=2)
		return cls._tick

	def _punch(self, **overrides):
		kwargs = {
			"employee": self.emp.name,
			"log_type": "IN",
			"pin": PIN,
			"device_id": "test-kiosk",
		}
		kwargs.update(overrides)
		with patch("timeclock.api.now_datetime", return_value=self._next_time()):
			return api.punch(**kwargs)

	def _badge_punch(self, badge_id):
		with patch("timeclock.api.now_datetime", return_value=self._next_time()):
			return api.punch_badge(badge_id=badge_id, device_id="test-kiosk")

	# ---- config ----

	def test_kiosk_config_flags_and_server_time(self):
		config = api.get_kiosk_config()
		self.assertIn("show_camera_preview", config)
		self.assertIn("play_sounds", config)
		self.assertIn(config["language"], ("de", "en"))
		# server_time drives the kiosk clock sync — must parse as a datetime
		self.assertIn("server_time", config)
		frappe.utils.get_datetime(config["server_time"])

	# ---- grid ----

	def test_grid_lists_only_enabled_employees(self):
		names = [e["name"] for e in api.get_kiosk_employees()]
		self.assertIn(self.emp.name, names)
		self.assertNotIn(self.emp_disabled.name, names)

	def test_grid_suggests_direction_from_last_log(self):
		self._punch(log_type="IN")
		entry = next(e for e in api.get_kiosk_employees() if e["name"] == self.emp.name)
		self.assertEqual(entry["last_log_type"], "IN")
		self.assertEqual(entry["suggested_log_type"], "OUT")

	# ---- PIN punch ----

	def test_punch_creates_checkin(self):
		result = self._punch(log_type="IN")
		self.assertEqual(result["log_type"], "IN")
		self.assertEqual(result["employee"], self.emp.name)
		device = frappe.db.get_value("Employee Checkin", result["name"], "device_id")
		self.assertEqual(device, "test-kiosk")

	def test_punch_wrong_pin_rejected(self):
		with self.assertRaises(frappe.ValidationError):
			self._punch(pin="9999")

	def test_punch_invalid_log_type_rejected(self):
		with self.assertRaises(frappe.ValidationError):
			self._punch(log_type="LUNCH")

	def test_punch_disabled_employee_rejected(self):
		with self.assertRaises(frappe.ValidationError):
			self._punch(employee=self.emp_disabled.name)

	def test_punch_lockout_after_max_attempts(self):
		for _i in range(api.MAX_PIN_ATTEMPTS):
			with self.assertRaises(frappe.ValidationError):
				self._punch(pin="9999")
		# even the CORRECT pin is refused while locked out
		with self.assertRaises(frappe.ValidationError):
			self._punch(pin=PIN)

	# ---- badge punch ----

	def test_badge_punch_toggles_direction(self):
		badge_id = api.generate_badge(self.emp.name)
		self._punch(log_type="IN")
		result = self._badge_punch(badge_id)
		self.assertEqual(result["log_type"], "OUT")
		result = self._badge_punch(badge_id)
		self.assertEqual(result["log_type"], "IN")

	def test_unknown_badge_rejected(self):
		with self.assertRaises(frappe.ValidationError):
			api.punch_badge(badge_id="definitely-not-a-badge", device_id="test-kiosk")

	def test_regenerating_badge_invalidates_old_one(self):
		old_badge = api.generate_badge(self.emp.name)
		new_badge = api.generate_badge(self.emp.name)
		self.assertNotEqual(old_badge, new_badge)
		with self.assertRaises(frappe.ValidationError):
			api.punch_badge(badge_id=old_badge, device_id="test-kiosk")

	# ---- undo ----

	def test_undo_deletes_recent_punch_from_same_device(self):
		result = self._punch()
		api.undo_punch(checkin=result["name"], device_id="test-kiosk")
		self.assertFalse(frappe.db.exists("Employee Checkin", result["name"]))

	def test_undo_from_other_device_rejected(self):
		result = self._punch()
		with self.assertRaises(frappe.PermissionError):
			api.undo_punch(checkin=result["name"], device_id="other-kiosk")

	def test_undo_after_window_rejected(self):
		result = self._punch()
		frappe.db.sql(
			"update `tabEmployee Checkin` set creation = timestampadd(second, %s, creation) where name = %s",
			(-(api.UNDO_WINDOW_SECONDS + 5), result["name"]),
		)
		with self.assertRaises(frappe.ValidationError):
			api.undo_punch(checkin=result["name"], device_id="test-kiosk")

	# ---- access control ----

	def test_kiosk_api_requires_role(self):
		user = "timeclock-test-norole@example.com"
		if not frappe.db.exists("User", user):
			frappe.get_doc(
				{
					"doctype": "User",
					"email": user,
					"first_name": "NoRole",
					"user_type": "Website User",
					"send_welcome_email": 0,
				}
			).insert(ignore_permissions=True)
		try:
			frappe.set_user(user)
			with self.assertRaises(frappe.PermissionError):
				api.get_kiosk_employees()
		finally:
			frappe.set_user("Administrator")

	# ---- settings validation ----

	def test_settings_reject_short_token(self):
		settings = frappe.get_doc("Timeclock Settings")
		settings.kiosk_autologin_token = "too-short"
		with self.assertRaises(frappe.ValidationError):
			settings.save()
		settings.reload()

	def test_settings_reject_system_manager_as_autologin_user(self):
		settings = frappe.get_doc("Timeclock Settings")
		settings.kiosk_autologin_user = "Administrator"
		settings.kiosk_autologin_token = "x" * 24
		with self.assertRaises(frappe.ValidationError):
			settings.save()
		settings.reload()

	# ---- badge rendering ----

	def test_badge_qr_svg(self):
		api.generate_badge(self.emp.name)
		from timeclock.badge import timeclock_badge_qr_svg

		svg = timeclock_badge_qr_svg(self.emp.name)
		self.assertIn("<svg", svg)
