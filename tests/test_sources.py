import datetime as dt
import os
import unittest

from _path import FIXTURES
from rh.config import DEFAULTS
from rh.sources import build_search_queries, normalize_api_repo, parse_trending, trending_url


class TrendingParseTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(os.path.join(FIXTURES, "trending.html"), encoding="utf-8") as f:
            cls.repos = parse_trending(f.read())

    def test_count(self):
        self.assertEqual(len(self.repos), 3)

    def test_first_repo_fields(self):
        r = self.repos[0]
        self.assertEqual(r["repo"], "thedotmack/claude-mem")
        self.assertEqual(r["language"], "TypeScript")
        self.assertEqual(r["stars"], 109970)
        self.assertEqual(r["forks"], 9600)
        self.assertEqual(r["stars_today"], 1526)
        self.assertTrue(r["description"].startswith("Persistent Context Across Sessions"))

    def test_repo_without_language(self):
        r = self.repos[2]
        self.assertEqual(r["repo"], "togg53192-cmd/jailbreaks")
        self.assertIsNone(r["language"])
        self.assertEqual(r["stars_today"], 726)

    def test_empty_page(self):
        self.assertEqual(parse_trending("<html></html>"), [])


class UrlAndQueryTest(unittest.TestCase):
    def test_trending_url(self):
        self.assertEqual(trending_url(""), "https://github.com/trending?since=daily")
        self.assertEqual(trending_url("c++"), "https://github.com/trending/c%2B%2B?since=daily")

    def test_search_queries(self):
        q = build_search_queries(dt.date(2026, 11, 2), DEFAULTS["search"])
        self.assertEqual(q, ["created:>=2026-10-03 stars:>=300", "pushed:>=2026-11-01 stars:>=1000"])

    def test_normalize_api_repo(self):
        r = normalize_api_repo({"full_name": "a/b", "stargazers_count": 5, "license": None, "archived": True})
        self.assertEqual(r["repo"], "a/b")
        self.assertEqual(r["stars"], 5)
        self.assertIsNone(r["license"])
        self.assertTrue(r["archived"])


if __name__ == "__main__":
    unittest.main()
