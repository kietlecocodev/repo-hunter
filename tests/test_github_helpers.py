import datetime as dt
import unittest

from _path import *  # noqa: F401,F403
from rh.github import classify_usage, farm_signals

TODAY = dt.date(2026, 11, 2)


class UsageTest(unittest.TestCase):
    def test_not_used(self):
        self.assertEqual(classify_usage("A/B", set(), set(), []), {"used": False, "reasons": []})

    def test_starred_case_insensitive(self):
        self.assertEqual(classify_usage("A/B", {"a/b"}, set(), [])["reasons"], ["starred"])

    def test_all_reasons(self):
        u = classify_usage("a/b", {"a/b"}, {"a/b"}, ["me/app"])
        self.assertTrue(u["used"])
        self.assertEqual(u["reasons"], ["starred", "forked", "mentioned in me/app"])


class FarmTest(unittest.TestCase):
    def test_clean(self):
        self.assertEqual(farm_signals({"stars": 5000, "forks": 400, "created_at": "2025-01-01T00:00:00Z"}, TODAY), [])

    def test_low_forks_and_young(self):
        s = farm_signals({"stars": 5000, "forks": 10, "created_at": "2026-10-25T00:00:00Z"}, TODAY)
        self.assertEqual(len(s), 2)

    def test_missing_fields(self):
        self.assertEqual(farm_signals({}, TODAY), [])


if __name__ == "__main__":
    unittest.main()
