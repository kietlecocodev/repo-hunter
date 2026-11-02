"""Tiny HTTP helpers for GitHub web/API calls, stdlib only."""
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

UA = "repo-hunter/0.1 (+https://github.com/kietlecocodev/repo-hunter)"
API = "https://api.github.com"


class FetchError(Exception):
    pass


class RateLimited(FetchError):
    pass


def github_token():
    for name in ("GH_READ_TOKEN", "GITHUB_TOKEN", "GH_TOKEN"):
        if os.environ.get(name):
            return os.environ[name]
    return None


def get(url, headers=None, timeout=30, retries=2, data=None):
    """Return (body_text, headers_dict). Raises RateLimited / FetchError."""
    h = {"User-Agent": UA}
    h.update(headers or {})
    for attempt in range(retries + 1):
        req = urllib.request.Request(url, headers=h, data=data)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode("utf-8", "replace"), {k.lower(): v for k, v in r.headers.items()}
        except urllib.error.HTTPError as e:
            remaining = e.headers.get("X-RateLimit-Remaining") if e.headers else None
            if e.code == 429 or (e.code == 403 and remaining == "0"):
                raise RateLimited(f"rate limited: {url}") from e
            if e.code >= 500 and attempt < retries:
                time.sleep(2 * (attempt + 1))
                continue
            raise FetchError(f"HTTP {e.code}: {url}") from e
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt < retries:
                time.sleep(2 * (attempt + 1))
                continue
            raise FetchError(f"{getattr(e, 'reason', e)}: {url}") from e
    raise FetchError(f"unreachable: {url}")


def api(path, params=None, token=None, accept="application/vnd.github+json", with_headers=False):
    url = path if path.startswith("http") else API + path
    if params:
        url += ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    h = {"Accept": accept, "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        h["Authorization"] = f"Bearer {token}"
    body, headers = get(url, h)
    data = json.loads(body) if body else None
    return (data, headers) if with_headers else data


def graphql(query, token):
    h = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    body, _ = get(API + "/graphql", h, data=json.dumps({"query": query}).encode())
    return json.loads(body)
