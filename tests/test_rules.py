import datetime as dt
import unittest

from _path import *  # noqa: F401,F403
from rh.config import DEFAULTS
from rh.rules import (NEW, RESUGGEST, SKIP, is_major_release, junk_reason, passes_threshold,
                      repeat_decision, resolve_stars_today, score, update_weights)

TODAY = dt.date(2026, 11, 2)


def cand(**kw):
    base = {"repo": "acme/tool", "description": "A useful tool", "license": "MIT", "archived": False, "fork": False}
    base.update(kw)
    return base


class ThresholdTest(unittest.TestCase):
    def test_boundary(self):
        self.assertTrue(passes_threshold(200, 200))
        self.assertFalse(passes_threshold(199, 200))
        self.assertFalse(passes_threshold(None, 200))

    def test_resolve_prefers_trending(self):
        self.assertEqual(resolve_stars_today(300, 250), (300, "trending"))
        self.assertEqual(resolve_stars_today(None, 250), (250, "snapshot"))
        self.assertEqual(resolve_stars_today(None, None), (None, None))


class JunkTest(unittest.TestCase):
    def test_clean(self):
        self.assertIsNone(junk_reason(cand(), DEFAULTS))

    def test_reasons(self):
        self.assertEqual(junk_reason(cand(archived=True), DEFAULTS), "archived")
        self.assertEqual(junk_reason(cand(fork=True), DEFAULTS), "fork")
        self.assertEqual(junk_reason(cand(license=None), dict(DEFAULTS, require_license=True)), "no license")
        self.assertEqual(junk_reason(cand(repo="x/awesome-llm"), DEFAULTS), "blocklist name: awesome")
        self.assertEqual(junk_reason(cand(description="A curated list of things"), DEFAULTS),
                         "blocklist desc: curated list")

    def test_name_token_not_substring(self):
        # "gamekit" is not the token "game"
        self.assertIsNone(junk_reason(cand(repo="x/gamekit"), DEFAULTS))

    def test_license_optional_by_default(self):
        self.assertIsNone(junk_reason(cand(license=None), DEFAULTS))


class RepeatTest(unittest.TestCase):
    def h(self, date, stars, fb=None):
        return {"date": date, "stars_today": stars, "feedback": fb}

    def test_new(self):
        self.assertEqual(repeat_decision([], 300, TODAY, 14, 2.0)[0], NEW)

    def test_skip_in_cooldown(self):
        self.assertEqual(repeat_decision([self.h("2026-10-30", 300)], 500, TODAY, 14, 2.0)[0], SKIP)

    def test_resuggest_on_double(self):
        self.assertEqual(repeat_decision([self.h("2026-10-30", 300)], 600, TODAY, 14, 2.0)[0], RESUGGEST)

    def test_resuggest_on_major_release(self):
        d = repeat_decision([self.h("2026-10-30", 300)], 300, TODAY, 14, 2.0, major_release_after_last=True)
        self.assertEqual(d[0], RESUGGEST)

    def test_after_cooldown(self):
        self.assertEqual(repeat_decision([self.h("2026-10-19", 300)], 250, TODAY, 14, 2.0)[0], RESUGGEST)

    def test_thumbs_down_forever(self):
        hist = [self.h("2026-08-01", 300, "👎")]
        self.assertEqual(repeat_decision(hist, 5000, TODAY, 14, 2.0)[0], SKIP)

    def test_uses_latest_entry(self):
        hist = [self.h("2026-10-01", 100), self.h("2026-10-31", 400)]
        self.assertEqual(repeat_decision(hist, 500, TODAY, 14, 2.0)[0], SKIP)


class MiscTest(unittest.TestCase):
    def test_major_release(self):
        self.assertTrue(is_major_release("v2.0.0"))
        self.assertTrue(is_major_release("3.0"))
        self.assertFalse(is_major_release("v2.1.0"))
        self.assertFalse(is_major_release("v0.0.0"))
        self.assertFalse(is_major_release(None))

    def test_weights_clamped(self):
        w = update_weights({"product": 1.98, "dev": 0.52, "design": 1.2},
                           [{"team": "Product", "feedback": "👍"}, {"team": "dev", "feedback": "👎"},
                            {"team": "design", "feedback": "Đã thử"}, {"team": "other", "feedback": "👍"}],
                           0.05, [0.5, 2.0])
        self.assertEqual(w, {"product": 2.0, "dev": 0.5, "design": 1.2})

    def test_score(self):
        self.assertEqual(score(1000, 1.5, 1.0), 4.5)
        self.assertEqual(score(0, 1.5, 1.0), 0.0)
        self.assertEqual(score(100, 1.0, 2.0), 2.0)


if __name__ == "__main__":
    unittest.main()
