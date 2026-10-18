"""Isolated generated candidate acceptance tests. Runs in no-network Docker only."""
import unittest
from datetime import datetime,timedelta,timezone
from generated.telemetry_fresh_candidate import telemetry_fresh

class GeneratedTelemetryTests(unittest.TestCase):
    def setUp(self):
        self.now=datetime(2026,10,18,12,0,0,tzinfo=timezone.utc)
    def test_fresh_and_edges(self):
        self.assertTrue(telemetry_fresh(self.now.isoformat(),self.now))
        self.assertTrue(telemetry_fresh((self.now-timedelta(seconds=180)).isoformat(),self.now))
    def test_stale_future_malformed(self):
        self.assertFalse(telemetry_fresh((self.now-timedelta(seconds=181)).isoformat(),self.now))
        self.assertFalse(telemetry_fresh((self.now+timedelta(seconds=1)).isoformat(),self.now))
        self.assertFalse(telemetry_fresh("not a timestamp",self.now))
        self.assertFalse(telemetry_fresh("",self.now))
    def test_now_must_be_timezone_aware(self):
        self.assertFalse(telemetry_fresh(self.now.isoformat(),self.now.replace(tzinfo=None)))
    def test_timestamp_must_be_timezone_aware(self):
        self.assertFalse(telemetry_fresh(self.now.replace(tzinfo=None).isoformat(),self.now))
    def test_offset_timestamps(self):
        offset=timezone(timedelta(hours=2))
        observed=(self.now-timedelta(seconds=10)).astimezone(offset)
        self.assertTrue(telemetry_fresh(observed.isoformat(),self.now))

    def test_fractional_second_boundary(self):
        valid=(self.now-timedelta(seconds=180)+timedelta(microseconds=1)).isoformat()
        stale=(self.now-timedelta(seconds=180,microseconds=1)).isoformat()
        self.assertTrue(telemetry_fresh(valid,self.now))
        self.assertFalse(telemetry_fresh(stale,self.now))
        self.assertFalse(telemetry_fresh((self.now+timedelta(microseconds=1)).isoformat(),self.now))

    def test_utc_z_and_cross_timezone_clock(self):
        self.assertTrue(telemetry_fresh("2026-10-18T12:00:00Z",self.now))
        india=timezone(timedelta(hours=5,minutes=30))
        self.assertTrue(telemetry_fresh(self.now.isoformat(),self.now.astimezone(india)))
        self.assertTrue(telemetry_fresh(
            (self.now-timedelta(seconds=179)).astimezone(india).isoformat(),self.now))
        self.assertFalse(telemetry_fresh(
            (self.now-timedelta(seconds=181)).astimezone(india).isoformat(),self.now))

    def test_wrong_input_types_fail_closed(self):
        self.assertFalse(telemetry_fresh(None,self.now))
        self.assertFalse(telemetry_fresh("",None))
        self.assertFalse(telemetry_fresh(self.now.isoformat(),None))

if __name__=="__main__":
    unittest.main()
