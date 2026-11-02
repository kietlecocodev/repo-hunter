"""Deterministic decision rules: threshold, junk filter, repeat rule, feedback weights."""
import datetime as dt
import re

NEW, RESUGGEST, SKIP = "new", "resuggest", "skip"
THUMBS_DOWN = "👎"
THUMBS_UP = "👍"


def resolve_stars_today(trending_value, snapshot_delta):
    """Trending's own number wins; otherwise snapshot delta. Returns (value, source)."""
    if trending_value is not None:
        return trending_value, "trending"
    if snapshot_delta is not None:
        return snapshot_delta, "snapshot"
    return None, None


def passes_threshold(stars_today, threshold):
    return stars_today is not None and stars_today >= threshold


def _name_tokens(repo):
    name = repo.split("/", 1)[-1].lower()
    return set(t for t in re.split(r"[^a-z0-9]+", name) if t)


def junk_reason(c, cfg):
    """Return a short reason string if candidate `c` should be dropped, else None."""
    if c.get("archived"):
        return "archived"
    if c.get("fork"):
        return "fork"
    if cfg.get("require_license") and not c.get("license"):
        return "no license"
    if c.get("license") == "NOASSERTION" and cfg.get("require_license"):
        return "unrecognized license"
    hits = _name_tokens(c["repo"]) & set(w.lower() for w in cfg["blocklist_name"])
    if hits:
        return f"blocklist name: {sorted(hits)[0]}"
    desc = (c.get("description") or "").lower()
    for phrase in cfg["blocklist_desc"]:
        if phrase.lower() in desc:
            return f"blocklist desc: {phrase}"
    return None


def repeat_decision(history, stars_today, today, cooldown_days, multiplier, major_release_after_last=False):
    """
    history: list of past suggestions for this repo: [{"date": iso, "stars_today": int, "feedback": str|None}]
    Returns (decision, reason).
      - never suggested            -> NEW
      - any 👎                      -> SKIP forever
      - last within cooldown        -> RESUGGEST if stars_today >= multiplier * last or new major release, else SKIP
      - last older than cooldown    -> RESUGGEST (still had to pass threshold today)
    """
    if not history:
        return NEW, "first time"
    if any(h.get("feedback") == THUMBS_DOWN for h in history):
        return SKIP, "user marked 👎"
    last = max(history, key=lambda h: h["date"])
    age = (today - dt.date.fromisoformat(last["date"])).days
    if age >= cooldown_days:
        return RESUGGEST, f"last suggested {age}d ago"
    need = multiplier * (last.get("stars_today") or 0)
    if stars_today >= need:
        return RESUGGEST, f"{stars_today} ≥ {multiplier:g}× last ({last.get('stars_today')})"
    if major_release_after_last:
        return RESUGGEST, "new major release since last suggestion"
    return SKIP, f"cooldown ({age}d < {cooldown_days}d), {stars_today} < {need:g}"


_MAJOR = re.compile(r"^v?(\d+)\.0(\.0)?$")


def is_major_release(tag):
    m = _MAJOR.match((tag or "").strip())
    return bool(m) and int(m.group(1)) >= 1


def update_weights(weights, feedback_items, step, bounds):
    """feedback_items: iterable of {"team": "product|design|dev", "feedback": "👍|👎|..."}."""
    lo, hi = bounds
    w = dict(weights)
    for f in feedback_items:
        team = (f.get("team") or "").lower()
        if team not in w:
            continue
        if f.get("feedback") == THUMBS_UP:
            w[team] += step
        elif f.get("feedback") == THUMBS_DOWN:
            w[team] -= step
        w[team] = round(min(hi, max(lo, w[team])), 4)
    return w


def score(stars_today, team_weight, fit):
    """Final ranking score used by the skill (spec §6.6)."""
    import math
    if not stars_today or stars_today <= 0:
        return 0.0
    return round(math.log10(stars_today) * team_weight * max(0.0, min(1.0, fit)), 3)
