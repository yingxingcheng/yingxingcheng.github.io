import datetime as dt
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import check_publication_due as schedule


class PublicationScheduleTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.record = Path(self.temp.name) / "publication-sync.json"
        self.today = dt.date(2026, 11, 6)

    def write_record(self, date):
        self.record.write_text(json.dumps({"last_successful_check": date}), encoding="utf-8")

    def due(self):
        return schedule.check_due(self.record, event="schedule", today=self.today)

    def test_missed_first_day_is_caught_up_later_in_month(self):
        self.write_record("2026-10-08")
        self.assertTrue(self.due())

    def test_success_this_month_skips_repeated_source_checks(self):
        for date in ("2026-11-01", "2026-11-06"):
            with self.subTest(date=date):
                self.write_record(date)
                self.assertFalse(self.due())

    def test_failure_without_success_record_is_retried(self):
        self.write_record("2026-10-08")
        before = self.record.read_bytes()
        self.assertTrue(self.due())
        self.assertTrue(self.due())
        self.assertEqual(self.record.read_bytes(), before)

    def test_next_month_and_year_are_due(self):
        for last, today in (
            ("2026-10-31", dt.date(2026, 11, 1)),
            ("2026-12-31", dt.date(2027, 1, 1)),
        ):
            with self.subTest(today=today):
                self.write_record(last)
                self.assertTrue(schedule.check_due(self.record, event="schedule", today=today))

    def test_future_date_does_not_suppress_check(self):
        for date in ("2026-11-07", "2027-11-01"):
            with self.subTest(date=date):
                self.write_record(date)
                self.assertTrue(self.due())

    def test_missing_or_invalid_record_is_due(self):
        self.assertTrue(self.due())
        for record in (
            "broken",
            "[]",
            "null",
            "{}",
            '{"last_successful_check": null}',
            '{"last_successful_check": "2026-02-30"}',
        ):
            with self.subTest(record=record):
                self.record.write_text(record, encoding="utf-8")
                self.assertTrue(self.due())

    def test_manual_run_always_refreshes(self):
        self.write_record("2026-11-06")
        self.assertTrue(
            schedule.check_due(self.record, event="workflow_dispatch", today=self.today)
        )

    def test_uses_utc_not_runner_local_date(self):
        self.write_record("2026-10-31")
        now = dt.datetime(2026, 11, 1, tzinfo=dt.timezone.utc)
        with patch.object(schedule.dt, "datetime") as clock:
            clock.now.return_value = now
            self.assertTrue(schedule.check_due(self.record, event="schedule"))
            clock.now.assert_called_once_with(dt.timezone.utc)

    def test_unknown_event_fails_closed(self):
        with self.assertRaises(ValueError):
            schedule.check_due(self.record, event="push", today=self.today)

    def test_cli_emits_boolean_only_and_does_not_write(self):
        self.write_record("2000-01-01")
        before = self.record.read_bytes()
        result = subprocess.run(
            [
                sys.executable,
                "check_publication_due.py",
                "--event",
                "schedule",
                "--record",
                str(self.record),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.stdout, "true\n")
        self.assertEqual(self.record.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
