"""GitHub lookups: metadata, star refresh, releases, star-farming sample, already-used check."""
import datetime as dt
import re
import time

from . import net
from .rules import is_major_release
from .sources import normalize_api_repo


# ---------- metadata & stars ----------

def repo_meta(repo, token):
    return normalize_api_repo(net.api(f"/repos/{repo}", token=token))


def refresh_stars(repos, token, rest_budget=40):
    """
    Current total stars for many repos -> ({lower_repo: stars}, errors).
    With a token: GraphQL in batches of 50. Without: REST for up to `rest_budget` repos.
    """
    repos = list(repos)
    out, errors = {}, []
    if not repos:
        return out, errors
    if token:
        for i in range(0, len(repos), 50):
            batch = repos[i:i + 50]
            parts = []
            for j, r in enumerate(batch):
                owner, name = r.split("/", 1)
                parts.append(f'r{j}: repository(owner: "{_gq(owner)}", name: "{_gq(name)}") {{ nameWithOwner stargazerCount }}')
            try:
                res = net.graphql("query {" + " ".join(parts) + "}", token)
            except net.FetchError as e:
                errors.append(f"graphql batch {i}: {e}")
                continue
            for node in (res.get("data") or {}).values():
                if node:
                    out[node["nameWithOwner"].lower()] = node["stargazerCount"]
        return out, errors
    for r in repos[:rest_budget]:
        try:
            out[r.lower()] = net.api(f"/repos/{r}")["stargazers_count"]
        except net.FetchError as e:
            errors.append(f"stars {r}: {e}")
            if isinstance(e, net.RateLimited):
                break
    if len(repos) > rest_budget:
        errors.append(f"no token: refreshed only {rest_budget}/{len(repos)} watchlist repos")
    return out, errors


def _gq(s):
    return re.sub(r'[^A-Za-z0-9_.\-]', "", s)


def major_release_since(repo, since_date, token):
    """True if the latest release is a major version published after `since_date` (date)."""
    try:
        rel = net.api(f"/repos/{repo}/releases/latest", token=token)
    except net.FetchError:
        return False
    published = (rel.get("published_at") or "")[:10]
    return bool(published) and published > since_date.isoformat() and is_major_release(rel.get("tag_name"))


# ---------- star farming ----------
# The stargazers list endpoint is no longer readable (401 anon / 404 with token, verified 2026-11-02),
# so we flag cheap signals instead of sampling accounts. Flagged repos are NOT dropped; Claude
# weighs the flag when assigning Risk.

def farm_signals(c, today):
    """Return a list of suspicious-star signals for candidate dict `c` (uses stars, forks, created_at)."""
    signals = []
    stars, forks = c.get("stars") or 0, c.get("forks") or 0
    created = (c.get("created_at") or "")[:10]
    age = (today - dt.date.fromisoformat(created)).days if created else None
    if stars >= 1000 and forks / max(stars, 1) < 0.01:
        signals.append(f"forks/stars {forks}/{stars} < 1%")
    if age is not None and age <= 14 and stars >= 3000:
        signals.append(f"{stars} stars in {age} days")
    return signals


# ---------- already used ----------

def starred_set(user, token):
    out, page = set(), 1
    while True:
        data = net.api(f"/users/{user}/starred", {"per_page": 100, "page": page}, token=token) or []
        out.update(r["full_name"].lower() for r in data)
        if len(data) < 100:
            return out
        page += 1


def fork_parents(user, token):
    """Lower-case full names of upstream repos that `user` has forked."""
    repos, page = [], 1
    while True:
        data = net.api(f"/users/{user}/repos", {"per_page": 100, "page": page, "type": "owner"}, token=token) or []
        repos.extend(data)
        if len(data) < 100:
            break
        page += 1
    parents = set()
    for r in repos:
        if not r.get("fork"):
            continue
        try:
            full = net.api(f"/repos/{r['full_name']}", token=token)
        except net.FetchError:
            continue
        src = full.get("parent") or full.get("source")
        if src:
            parents.add(src["full_name"].lower())
    return parents


def code_mentions(user, repo, token):
    """Repos of `user` whose code mentions "owner/name". Requires a token. Returns sorted list of full names."""
    data = net.api("/search/code", {"q": f'"{repo}" user:{user}', "per_page": 30}, token=token) or {}
    return sorted({it["repository"]["full_name"] for it in data.get("items") or []})


def classify_usage(repo, starred, forked, mentions):
    key = repo.lower()
    reasons = []
    if key in starred:
        reasons.append("starred")
    if key in forked:
        reasons.append("forked")
    if mentions:
        reasons.append("mentioned in " + ", ".join(mentions))
    return {"used": bool(reasons), "reasons": reasons}


def check_used(user, repos, token, code_search=False, pause=6.5):
    """-> ({lower_repo: {"used": bool, "reasons": [...]}}, errors). Code search (slow: 10/min) only if asked."""
    errors = []
    try:
        starred = starred_set(user, token)
    except net.FetchError as e:
        starred, errors = set(), errors + [f"starred: {e}"]
    try:
        forked = fork_parents(user, token)
    except net.FetchError as e:
        forked, errors = set(), errors + [f"forks: {e}"]
    if code_search and not token:
        errors.append("no token: code search skipped (only star/fork checked)")
    out = {}
    for i, r in enumerate(repos):
        mentions = []
        if code_search and token:
            if i:
                time.sleep(pause)  # code search: 10 req/min
            try:
                mentions = code_mentions(user, r, token)
            except net.FetchError as e:
                errors.append(f"code search {r}: {e}")
        out[r.lower()] = classify_usage(r, starred, forked, mentions)
    return out, errors
