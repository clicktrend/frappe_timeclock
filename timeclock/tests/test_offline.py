# Copyright (c) 2026, Adomio · Yücel & Tirgil GbR and contributors
# For license information, please see license.txt

import uuid
from datetime import datetime, timedelta
from unittest.mock import patch

import frappe
from frappe.utils import now_datetime

try:
	from frappe.tests import IntegrationTestCase
except ImportError:  # frappe < v16
	from frappe.tests.utils import FrappeTestCase as IntegrationTestCase

from timeclock import api, offline
from timeclock.tests.test_api import PIN, _make_employee

DEVICE = "test-offline-kiosk"


def _fmt(dt: datetime) -> str:
	return dt.strftime("%Y-%m-%d %H:%M:%S")


class TestOfflinePunches(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")
		cls.emp = _make_employee("Offline", enabled=True, pin=PIN)
		cls.badge = api.generate_badge(cls.emp.name)
		# every punch gets its own ten minutes (outside the duplicate window), still inside the offline window
		cls._tick = now_datetime() - timedelta(hours=60)

	def setUp(self):
		frappe.set_user("Administrator")

	@classmethod
	def _next_time(cls):
		cls._tick += timedelta(minutes=10)
		return cls._tick

	def _punch(self, **overrides):
		claimed = self._next_time()
		punch = {
			"client_uuid": uuid.uuid4().hex,
			"method": "PIN",
			"employee": self.emp.name,
			"pin": PIN,
			"log_type": "IN",
			"claimed_time": _fmt(claimed),
			"device_time": _fmt(claimed),
			"clock_offset_ms": 0,
			"clock_synced_at": _fmt(claimed - timedelta(minutes=30)),
		}
		punch.update(overrides)
		return punch

	def _sync(self, *punches):
		return api.sync_offline_punches(device_id=DEVICE, punches=list(punches))

	def _queued(self, result):
		return frappe.get_doc("Timeclock Queued Punch", result["name"])

	# ---- booking ----

	def test_valid_pin_punch_is_booked_with_claimed_time(self):
		punch = self._punch(log_type="IN")
		[result] = self._sync(punch)
		self.assertEqual(result["status"], "Booked")

		queued = self._queued(result)
		checkin = frappe.get_doc("Employee Checkin", queued.checkin)
		self.assertEqual(str(checkin.time), punch["claimed_time"])
		self.assertEqual(checkin.log_type, "IN")
		self.assertEqual(checkin.device_id, DEVICE)
		self.assertEqual(checkin.timeclock_queued_punch, queued.name)

	def test_retried_sync_does_not_book_twice(self):
		punch = self._punch()
		[first] = self._sync(punch)
		[second] = self._sync(punch)
		self.assertEqual(first["name"], second["name"])
		self.assertEqual(frappe.db.count("Employee Checkin", {"timeclock_queued_punch": first["name"]}), 1)

	def test_badge_toggles_from_last_checkin_before_punch_time(self):
		[first] = self._sync(self._punch(log_type="IN"))
		self.assertEqual(first["status"], "Booked")
		badge = self._punch(method="Badge", badge_id=self.badge, employee=None, pin=None, log_type=None)
		[result] = self._sync(badge)
		self.assertEqual(result["status"], "Booked")
		self.assertEqual(result["log_type"], "OUT")

	def test_batch_is_booked_in_claimed_order(self):
		early, late = self._punch(log_type="IN"), self._punch(method="Badge", badge_id=self.badge)
		# sent in the wrong order: the badge must still see the IN before it
		results = {r["client_uuid"]: r for r in self._sync(late, early)}
		self.assertEqual(results[late["client_uuid"]]["log_type"], "OUT")

	# ---- quarantine ----

	def test_wrong_pin_goes_to_quarantine(self):
		[result] = self._sync(self._punch(pin="9999"))
		self.assertEqual(result["status"], "Quarantine")
		queued = self._queued(result)
		self.assertFalse(queued.checkin)
		self.assertIn("PIN", queued.reason)

	def test_pin_is_never_stored(self):
		[result] = self._sync(self._punch(pin="9999"))
		queued = self._queued(result).as_dict()
		self.assertNotIn("9999", frappe.as_json(queued))

	def test_unknown_badge_keeps_only_a_hash(self):
		secret = uuid.uuid4().hex
		[result] = self._sync(self._punch(method="Badge", badge_id=secret, employee=None))
		self.assertEqual(result["status"], "Quarantine")
		queued = self._queued(result)
		self.assertEqual(queued.badge_hash, offline.badge_hash(secret))
		self.assertNotIn(secret, frappe.as_json(queued.as_dict()))

	def test_never_synced_clock_goes_to_quarantine(self):
		[result] = self._sync(self._punch(clock_synced_at=None))
		self.assertEqual(result["status"], "Quarantine")

	def test_future_time_goes_to_quarantine(self):
		future = now_datetime() + timedelta(hours=1)
		[result] = self._sync(self._punch(claimed_time=_fmt(future)))
		self.assertEqual(result["status"], "Quarantine")

	def test_too_old_punch_goes_to_quarantine(self):
		old = now_datetime() - timedelta(hours=100)
		[result] = self._sync(self._punch(claimed_time=_fmt(old)))
		self.assertEqual(result["status"], "Quarantine")

	def test_duplicate_timestamp_is_held_not_lost(self):
		punch = self._punch()
		self._sync(punch)
		twin = dict(punch, client_uuid=uuid.uuid4().hex)
		[result] = self._sync(twin)
		self.assertEqual(result["status"], "Quarantine")

	def test_near_duplicate_of_online_punch_is_held(self):
		punch = self._punch(log_type="OUT")
		self._sync(punch)
		claimed = frappe.utils.get_datetime(punch["claimed_time"])
		echo = self._punch(log_type="OUT", claimed_time=_fmt(claimed + timedelta(seconds=40)))
		[result] = self._sync(echo)
		self.assertEqual(result["status"], "Quarantine")
		self.assertIn("duplicate", self._queued(result).reason)

	def test_hr_can_book_and_discard_quarantined(self):
		[held] = self._sync(self._punch(pin="0000", log_type="OUT"))
		self.assertEqual(api.book_queued_punch(name=held["name"]), "Booked")
		self.assertTrue(self._queued(held).checkin)

		[other] = self._sync(self._punch(pin="0000"))
		self.assertEqual(api.discard_queued_punch(name=other["name"]), "Discarded")
		with self.assertRaises(frappe.ValidationError):
			api.book_queued_punch(name=other["name"])

	# ---- attendance conflict ----

	def test_existing_attendance_is_flagged(self):
		punch = self._punch()
		day = punch["claimed_time"][:10]
		attendance = frappe.get_doc(
			{
				"doctype": "Attendance",
				"employee": self.emp.name,
				"attendance_date": day,
				"status": "Absent",
				"company": self.emp.company,
			}
		).insert(ignore_permissions=True)
		with patch("timeclock.offline._notify_attendance_conflicts") as notify:
			[result] = self._sync(punch)
		self.assertEqual(self._queued(result).attendance, attendance.name)
		notify.assert_called_once()
		attendance.delete(ignore_permissions=True)

	# ---- devices ----

	def test_heartbeat_registers_and_flags_outdated_build(self):
		with patch("timeclock.offline.current_kiosk_build", return_value="NEW"):
			reply = api.heartbeat(device_id="test-hb-kiosk", version="0.2.0", build="OLD", pending=3)
		self.assertTrue(reply["reload"])
		device = frappe.get_doc("Timeclock Device", "test-hb-kiosk")
		self.assertEqual(device.status, "Online")
		self.assertEqual(device.pending_punches, 3)
		self.assertTrue(device.outdated)

	def test_silent_device_goes_offline_and_alerts_once(self):
		api.heartbeat(device_id="test-silent-kiosk", version="0.2.0", build="X", pending=0)
		frappe.db.set_value(
			"Timeclock Device", "test-silent-kiosk", "last_seen", now_datetime() - timedelta(minutes=30)
		)
		settings = frappe.get_doc("Timeclock Settings")
		settings.device_alert_minutes = 15
		settings.device_alert_recipients = "hr@example.com"
		settings.device_alert_from = "00:00:00"
		settings.device_alert_to = "23:59:59"
		settings.device_alert_weekends = 1
		settings.save()

		with patch("timeclock.offline.frappe.sendmail") as sendmail:
			offline.check_devices()
			offline.check_devices()
		self.assertEqual(frappe.db.get_value("Timeclock Device", "test-silent-kiosk", "status"), "Offline")
		self.assertEqual(sendmail.call_count, 1)

		with patch("timeclock.offline.frappe.sendmail") as sendmail:
			api.heartbeat(device_id="test-silent-kiosk", version="0.2.0", build="X", pending=0)
		sendmail.assert_called_once()  # recovery notice
		self.assertEqual(frappe.db.get_value("Timeclock Device", "test-silent-kiosk", "alert_sent"), 0)

	def test_invalid_device_id_rejected(self):
		with self.assertRaises(frappe.ValidationError):
			api.heartbeat(device_id="../etc", version="x", build="x")
