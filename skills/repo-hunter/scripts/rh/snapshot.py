"""Daily star snapshots + watchlist (state lives in the private state repo)."""
import datetime as dt
import json
import os
import re

_DATE_FILE = re.compile(r"^(\d{4}-\d{2}-\d{2})\.json$")


def _snap_dir(state_dir):
    return os.path.join(state_dir, "state", "snapshots")


def read_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")
    os.replace(tmp, path)


def save_snapshot(state_dir, date, stars_by_repo):
    """stars_by_repo: {lower_repo: total_stars}."""
    write_json(os.path.join(_snap_dir(state_dir), f"{date.isoformat()}.json"), stars_by_repo)


def previous_snapshot(state_dir, date):
    """Latest snapshot strictly before `date` -> (date, mapping) or (None, {})."""
    d = _snap_dir(state_dir)
    if not os.path.isdir(d):
        return None, {}
    dates = sorted(m.group(1) for m in map(_DATE_FILE.match, os.listdir(d)) if m)
    dates = [x for x in dates if x < date.isoformat()]
    if not dates:
        return None, {}
    prev = dates[-1]
    return dt.date.fromisoformat(prev), read_json(os.path.join(d, f"{prev}.json"), {})


def daily_delta(now_stars, prev_stars, days):
    """Average stars/day between two snapshots `days` apart."""
    if now_stars is None or prev_stars is None or days <= 0:
        return None
    return round((now_stars - prev_stars) / days)


def prune_snapshots(state_dir, today, keep_days=45):
    d = _snap_dir(state_dir)
    if not os.path.isdir(d):
        return 0
    cutoff = (today - dt.timedelta(days=keep_days)).isoformat()
    removed = 0
    for name in os.listdir(d):
        m = _DATE_FILE.match(name)
        if m and m.group(1) < cutoff:
            os.remove(os.path.join(d, name))
            removed += 1
    return removed


def update_watchlist(watchlist, repos, spikes, today, stale_days, max_size):
    """
    watchlist: {lower_repo: {"added": iso, "last_spike": iso|None}}
    repos: iterable of lower_repo seen today (added if new)
    spikes: set of lower_repo that crossed the threshold today
    Drops entries with no spike for `stale_days` (counting from added if never spiked),
    then caps to `max_size`, keeping the most recently active.
    """
    t = today.isoformat()
    wl = {k: dict(v) for k, v in watchlist.items()}
    for r in repos:
        wl.setdefault(r, {"added": t, "last_spike": None})
    for r in spikes:
        wl.setdefault(r, {"added": t, "last_spike": None})["last_spike"] = t
    cutoff = (today - dt.timedelta(days=stale_days)).isoformat()
    wl = {k: v for k, v in wl.items() if (v["last_spike"] or v["added"]) >= cutoff}
    if len(wl) > max_size:
        ranked = sorted(wl.items(), key=lambda kv: (kv[1]["last_spike"] or kv[1]["added"], kv[0]), reverse=True)
        wl = dict(ranked[:max_size])
    return wl
