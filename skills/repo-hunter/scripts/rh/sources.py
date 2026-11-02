"""Candidate sources: GitHub Trending (A) and Search API (B).

OSS Insight trending was evaluated as a fallback but its ranking is unavailable
since 2026-03-01 (API returns data_quality.status=unavailable), so it is not used.
"""
import datetime as dt
import html as htmllib
import re
import time
import urllib.parse

from . import net

_ARTICLE = re.compile(r'<article class="Box-row">(.*?)</article>', re.S)
_REPO = re.compile(r'<h2[^>]*>.*?href="/([^"/\s]+/[^"/\s]+)"', re.S)
_DESC = re.compile(r'<p class="[^"]*">(.*?)</p>', re.S)
_LANG = re.compile(r'itemprop="programmingLanguage">([^<]*)<')
_STARS = re.compile(r'href="/[^"]+/stargazers"[^>]*>(.*?)</a>', re.S)
_FORKS = re.compile(r'href="/[^"]+/forks"[^>]*>(.*?)</a>', re.S)
_TODAY = re.compile(r'([\d,]+)\s+stars?\s+today')


def _text(fragment):
    return re.sub(r"\s+", " ", htmllib.unescape(re.sub(r"<[^>]+>", "", fragment))).strip()


def _num(fragment):
    digits = re.sub(r"[^\d]", "", _text(fragment))
    return int(digits) if digits else 0


def parse_trending(page):
    """Parse a github.com/trending page into repo dicts."""
    out = []
    for art in _ARTICLE.findall(page):
        m = _REPO.search(art)
        if not m:
            continue
        desc, lang = _DESC.search(art), _LANG.search(art)
        stars, forks, today = _STARS.search(art), _FORKS.search(art), _TODAY.search(art)
        out.append({
            "repo": m.group(1),
            "description": _text(desc.group(1)) if desc else "",
            "language": _text(lang.group(1)) if lang else None,
            "stars": _num(stars.group(1)) if stars else 0,
            "forks": _num(forks.group(1)) if forks else 0,
            "stars_today": _num(today.group(1)) if today else 0,
        })
    return out


def trending_url(language):
    path = "/" + urllib.parse.quote(language) if language else ""
    return f"https://github.com/trending{path}?since=daily"


def fetch_trending(languages, pause=1.0):
    """Return (repos_by_lower_name, errors). Same repo across pages keeps max stars_today."""
    found, errors = {}, []
    for i, lang in enumerate(languages):
        if i:
            time.sleep(pause)
        try:
            page, _ = net.get(trending_url(lang))
        except net.FetchError as e:
            errors.append(f"trending[{lang or 'all'}]: {e}")
            continue
        for r in parse_trending(page):
            key = r["repo"].lower()
            if key not in found or r["stars_today"] > found[key]["stars_today"]:
                found[key] = r
    return found, errors


def build_search_queries(today, cfg_search):
    """Two daily queries (spec §5). `today` is a date."""
    new_since = (today - dt.timedelta(days=cfg_search["new_repo_days"])).isoformat()
    yesterday = (today - dt.timedelta(days=1)).isoformat()
    return [
        f"created:>={new_since} stars:>={cfg_search['new_repo_min_stars']}",
        f"pushed:>={yesterday} stars:>={cfg_search['active_min_stars']}",
    ]


def normalize_api_repo(item):
    lic = item.get("license") or {}
    return {
        "repo": item["full_name"],
        "description": item.get("description") or "",
        "language": item.get("language"),
        "stars": item.get("stargazers_count", 0),
        "forks": item.get("forks_count", 0),
        "archived": bool(item.get("archived")),
        "fork": bool(item.get("fork")),
        "license": lic.get("spdx_id") if lic else None,
        "topics": item.get("topics") or [],
        "created_at": item.get("created_at"),
        "pushed_at": item.get("pushed_at"),
        "homepage": item.get("homepage") or "",
    }


def search_repos(queries, token, per_query=300):
    """Return (repos_by_lower_name, errors). Stops a query early on rate limit."""
    found, errors = {}, []
    for q in queries:
        for page in range(1, per_query // 100 + 1):
            try:
                data = net.api("/search/repositories",
                               {"q": q, "sort": "stars", "order": "desc", "per_page": 100, "page": page},
                               token=token)
            except net.FetchError as e:
                errors.append(f"search[{q}] p{page}: {e}")
                break
            items = (data or {}).get("items") or []
            for it in items:
                r = normalize_api_repo(it)
                found[r["repo"].lower()] = r
            if len(items) < 100:
                break
            time.sleep(2 if token else 7)  # search API: 30/min auth, 10/min anon
    return found, errors
