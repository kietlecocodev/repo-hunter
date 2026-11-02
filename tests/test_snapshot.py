import datetime as dt
import tempfile
import unittest

from _path import *  # noqa: F401,F403
from rh.snapshot import daily_delta, previous_snapshot, prune_snapshots, save_snapshot, update_watchlist

D = dt.date


class SnapshotTest(unittest.TestCase):
    def test_previous_snapshot_picks_latest_before_today(self):
        with tempfile.TemporaryDirectory() as d:
            save_snapshot(d, D(2026, 10, 30), {"a/b": 1})
            save_snapshot(d, D(2026, 11, 1), {"a/b": 2})
            save_snapshot(d, D(2026, 11, 2), {"a/b": 3})
            date, snap = previous_snapshot(d, D(2026, 11, 2))
            self.assertEqual(date, D(2026, 11, 1))
            self.assertEqual(snap, {"a/b": 2})

    def test_previous_snapshot_none(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(previous_snapshot(d, D(2026, 11, 2)), (None, {}))

    def test_daily_delta(self):
        self.assertEqual(daily_delta(1500, 1000, 1), 500)
        self.assertEqual(daily_delta(1600, 1000, 3), 200)
        self.assertIsNone(daily_delta(1600, None, 1))
        self.assertIsNone(daily_delta(1600, 1000, 0))

    def test_prune(self):
        with tempfile.TemporaryDirectory() as d:
            save_snapshot(d, D(2026, 9, 1), {})
            save_snapshot(d, D(2026, 11, 1), {})
            self.assertEqual(prune_snapshots(d, D(2026, 11, 2), keep_days=45), 1)
            self.assertEqual(previous_snapshot(d, D(2026, 11, 2))[0], D(2026, 11, 1))


class WatchlistTest(unittest.TestCase):
    today = D(2026, 11, 2)

    def test_adds_and_marks_spikes(self):
        wl = update_watchlist({}, ["a/b", "c/d"], {"c/d"}, self.today, 30, 10)
        self.assertEqual(wl["a/b"], {"added": "2026-11-02", "last_spike": None})
        self.assertEqual(wl["c/d"]["last_spike"], "2026-11-02")

    def test_prunes_stale(self):
        old = {"x/y": {"added": "2026-09-01", "last_spike": None},
               "z/w": {"added": "2026-09-01", "last_spike": "2026-10-20"}}
        wl = update_watchlist(old, [], set(), self.today, 30, 10)
        self.assertEqual(set(wl), {"z/w"})

    def test_caps_size_keeping_recent(self):
        old = {"old/a": {"added": "2026-10-10", "last_spike": None},
               "new/b": {"added": "2026-11-01", "last_spike": None}}
        wl = update_watchlist(old, ["today/c"], set(), self.today, 30, 2)
        self.assertEqual(set(wl), {"today/c", "new/b"})


if __name__ == "__main__":
    unittest.main()
