import datetime as dt
import json
import os
import tempfile
import unittest
from unittest import mock

from _path import *  # noqa: F401,F403
from rh import pipeline, snapshot
from rh.config import DEFAULTS

TODAY = dt.date(2026, 11, 2)


def trending_repo(name, today, stars):
    return {"repo": name, "description": "tool", "language": "Python", "stars": stars, "forks": 1, "stars_today": today}


def meta(name, **kw):
    m = {"repo": name, "description": "tool", "language": "Python", "stars": 0, "forks": 0,
         "archived": False, "fork": False, "license": "MIT", "topics": []}
    m.update(kw)
    return m


class PipelineTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.state = self.tmp.name
        self.cfg = dict(DEFAULTS, github_user="me", languages=[""])
        # yesterday's snapshot lets search-only repo get a delta
        snapshot.save_snapshot(self.state, TODAY - dt.timedelta(days=1), {"b/search-hot": 1000, "c/search-slow": 5000})
        snapshot.write_json(os.path.join(self.state, "state", "suggested.json"), {
            "d/repeat": [{"date": "2026-10-31", "stars_today": 400, "feedback": None}],
        })

    def tearDown(self):
        self.tmp.cleanup()

    def run_collect(self, dry_run=False):
        trending = {
            "a/trend-hot": trending_repo("a/trend-hot", 900, 10000),
            "x/awesome-things": trending_repo("x/awesome-things", 800, 5000),
            "d/repeat": trending_repo("d/repeat", 500, 7000),
            "e/used": trending_repo("e/used", 300, 3000),
            "f/small": trending_repo("f/small", 50, 3000),
        }
        searched = {
            "b/search-hot": dict(meta("b/search-hot"), stars=1350),
            "c/search-slow": dict(meta("c/search-slow"), stars=5100),
        }

        def fake_meta(name, token):
            return meta(name)

        usage = {"a/trend-hot": {"used": False, "reasons": []},
                 "b/search-hot": {"used": False, "reasons": []},
                 "e/used": {"used": True, "reasons": ["starred"]}}
        with mock.patch.object(pipeline.sources, "fetch_trending", return_value=(trending, [])), \
             mock.patch.object(pipeline.sources, "search_repos", return_value=(searched, [])), \
             mock.patch.object(pipeline.github, "refresh_stars", return_value=({}, [])), \
             mock.patch.object(pipeline.github, "repo_meta", side_effect=fake_meta), \
             mock.patch.object(pipeline.github, "major_release_since", return_value=False), \
             mock.patch.object(pipeline.github, "check_used", return_value=(usage, [])):
            return pipeline.collect(self.state, self.cfg, TODAY, token=None, dry_run=dry_run)

    def test_counts_and_candidates(self):
        summary, candidates, steps = self.run_collect()
        names = [c["repo"] for c in candidates]
        self.assertEqual(names, ["a/trend-hot", "b/search-hot"])
        self.assertEqual(candidates[1]["stars_today"], 350)
        self.assertEqual(candidates[1]["stars_today_source"], "snapshot")
        c = summary["counts"]
        self.assertEqual(c["candidates"], 7)
        self.assertEqual(c["over_threshold"], 5)   # a, x, d, e, b
        self.assertEqual(c["after_filters"], 3)    # a, e, b (x junk, d repeat)
        self.assertEqual(c["already_used"], 1)
        self.assertEqual(c["to_review"], 2)
        self.assertEqual(summary["sources"], ["Trending", "Search API", "Snapshot delta"])
        self.assertIn("x/awesome-things", summary["dropped"]["junk"])
        self.assertIn("d/repeat", summary["dropped"]["repeat"])
        self.assertEqual(summary["dropped"]["used"], {"e/used": ["starred"]})
        self.assertEqual(summary["status"], "Success")
        self.assertEqual([s["step"] for s in steps][-1], "star_farming")

    def test_persists_state(self):
        self.run_collect()
        rd = pipeline.run_dir(self.state, TODAY)
        self.assertTrue(os.path.exists(os.path.join(rd, "candidates.json")))
        self.assertTrue(os.path.exists(os.path.join(rd, "log.json")))
        snap_date, snap = snapshot.previous_snapshot(self.state, TODAY + dt.timedelta(days=1))
        self.assertEqual(snap_date, TODAY)
        self.assertEqual(snap["b/search-hot"], 1350)
        wl = snapshot.read_json(os.path.join(self.state, "state", "watchlist.json"), {})
        self.assertEqual(wl["a/trend-hot"]["last_spike"], "2026-11-02")

    def test_dry_run_writes_nothing(self):
        self.run_collect(dry_run=True)
        self.assertFalse(os.path.exists(pipeline.run_dir(self.state, TODAY)))
        self.assertEqual(snapshot.previous_snapshot(self.state, TODAY + dt.timedelta(days=1))[0],
                         TODAY - dt.timedelta(days=1))

    def test_record_and_feedback(self):
        picks = [{"repo": "A/Trend-Hot", "team": "product", "stars_today": 900, "score": 4.4}]
        pipeline.record(self.state, TODAY, picks)
        pipeline.record(self.state, TODAY, picks)  # idempotent
        sug = snapshot.read_json(os.path.join(self.state, "state", "suggested.json"), {})
        self.assertEqual(len(sug["a/trend-hot"]), 1)
        changed, w = pipeline.apply_feedback(self.state, self.cfg,
                                             [{"repo": "a/trend-hot", "date": "2026-11-02", "feedback": "👍"}])
        self.assertEqual(changed, 1)
        self.assertEqual(w["product"], 1.55)
        changed, w = pipeline.apply_feedback(self.state, self.cfg,
                                             [{"repo": "a/trend-hot", "date": "2026-11-02", "feedback": "👍"}])
        self.assertEqual((changed, w["product"]), (0, 1.55))  # no double count

    def test_failed_when_no_sources(self):
        with mock.patch.object(pipeline.sources, "fetch_trending", return_value=({}, ["boom"])), \
             mock.patch.object(pipeline.sources, "search_repos", return_value=({}, ["boom"])), \
             mock.patch.object(pipeline.github, "refresh_stars", return_value=({}, [])):
            summary, candidates, _ = pipeline.collect(self.state, self.cfg, TODAY, token=None)
        self.assertEqual(summary["status"], "Failed")
        self.assertEqual(candidates, [])


if __name__ == "__main__":
    unittest.main()
