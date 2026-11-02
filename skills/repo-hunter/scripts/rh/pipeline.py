"""Daily pipeline: collect -> threshold -> junk -> repeat -> used(star/fork) -> farm signals -> candidates.json; verify = code search on shortlist."""
import datetime as dt
import os

from . import github, net, snapshot, sources
from .rules import (NEW, RESUGGEST, SKIP, junk_reason, passes_threshold, repeat_decision,
                    resolve_stars_today, update_weights)


def run_dir(state_dir, date):
    return os.path.join(state_dir, "state", "runs", date.isoformat())


def _paths(state_dir):
    s = os.path.join(state_dir, "state")
    return {
        "watchlist": os.path.join(s, "watchlist.json"),
        "suggested": os.path.join(s, "suggested.json"),
        "weights": os.path.join(s, "weights.json"),
    }


class Log:
    def __init__(self):
        self.steps, self.errors = [], []

    def step(self, name, count_in, count_out, note=""):
        self.steps.append({
            "at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "step": name, "in": count_in, "out": count_out, "note": note,
        })

    def err(self, items):
        self.errors.extend(items)


def collect(state_dir, cfg, today, token, dry_run=False):
    log = Log()
    paths = _paths(state_dir)
    sources_used = []

    # 1. Source A: trending
    trending, errs = sources.fetch_trending(cfg["languages"])
    log.err(errs)
    if trending:
        sources_used.append("Trending")
    log.step("trending", len(cfg["languages"]), len(trending), f"{len(cfg['languages'])} language pages")

    # 2. Source B: search API
    queries = sources.build_search_queries(today, cfg["search"])
    searched, errs = sources.search_repos(queries, token, cfg["search"]["per_query"])
    log.err(errs)
    if searched:
        sources_used.append("Search API")
    log.step("search_api", len(queries), len(searched), " | ".join(queries))

    # 3. Current totals for everything we track
    watchlist = snapshot.read_json(paths["watchlist"], {})
    stars_now = {k: v["stars"] for k, v in searched.items() if v.get("stars") is not None}
    stars_now.update({k: v["stars"] for k, v in trending.items() if v.get("stars")})
    to_refresh = [k for k in watchlist if k not in stars_now]
    refreshed, errs = github.refresh_stars(to_refresh, token)
    log.err(errs)
    stars_now.update(refreshed)
    log.step("refresh_watchlist", len(to_refresh), len(refreshed), f"watchlist size {len(watchlist)}")

    # 4. Snapshot delta (A + B combined)
    prev_date, prev = snapshot.previous_snapshot(state_dir, today)
    days = (today - prev_date).days if prev_date else 0
    pool = {}
    for key in set(trending) | set(searched) | set(refreshed):
        info = {}
        info.update(searched.get(key, {}))
        info.update({k: v for k, v in trending.get(key, {}).items() if v is not None})
        if "repo" not in info:
            info["repo"] = key
        info["stars"] = stars_now.get(key, info.get("stars"))
        delta = snapshot.daily_delta(stars_now.get(key), prev.get(key), days) if prev_date else None
        value, src = resolve_stars_today(trending[key]["stars_today"] if key in trending else None, delta)
        info.update({"stars_today": value, "stars_today_source": src, "snapshot_delta": delta})
        pool[key] = info
    if any(c["stars_today_source"] == "snapshot" for c in pool.values()):
        sources_used.append("Snapshot delta")
    note = f"prev snapshot {prev_date} ({days}d)" if prev_date else "no previous snapshot: delta unavailable today"
    log.step("merge", len(trending) + len(searched) + len(refreshed), len(pool), note)

    # 5. Threshold
    over = {k: c for k, c in pool.items() if passes_threshold(c["stars_today"], cfg["threshold"])}
    log.step("threshold", len(pool), len(over), f"stars_today >= {cfg['threshold']}")

    # 6. Metadata + junk filter
    kept, junk = {}, {}
    for k, c in over.items():
        if "license" not in c:
            try:
                meta = github.repo_meta(c["repo"], token)
                meta.update({x: c[x] for x in ("stars_today", "stars_today_source", "snapshot_delta")})
                c = meta
            except net.FetchError as e:
                log.err([f"meta {c['repo']}: {e}"])
                c = dict(c, license="UNKNOWN", meta_error=True)
        reason = junk_reason(c, cfg)
        if reason:
            junk[c["repo"]] = reason
        else:
            kept[k] = c
    log.step("junk_filter", len(over), len(kept), "; ".join(f"{r}: {why}" for r, why in sorted(junk.items())))

    # 7. Repeat rule
    suggested = snapshot.read_json(paths["suggested"], {})
    fresh, skipped = {}, {}
    for k, c in kept.items():
        hist = suggested.get(k, [])
        decision, why = repeat_decision(hist, c["stars_today"], today, cfg["cooldown_days"], cfg["resuggest_multiplier"])
        if decision == SKIP and hist and "cooldown" in why:
            last = dt.date.fromisoformat(max(h["date"] for h in hist))
            if github.major_release_since(c["repo"], last, token):
                decision, why = repeat_decision(hist, c["stars_today"], today, cfg["cooldown_days"],
                                                cfg["resuggest_multiplier"], major_release_after_last=True)
        if decision == SKIP:
            skipped[c["repo"]] = why
        else:
            fresh[k] = dict(c, resuggest=(decision == RESUGGEST), repeat_reason=why)
    log.step("repeat_rule", len(kept), len(fresh), "; ".join(f"{r}: {why}" for r, why in sorted(skipped.items())))

    # 8. Already used (star / fork / code search)
    used = {}
    if cfg["github_user"] and fresh:
        usage, errs = github.check_used(cfg["github_user"], [c["repo"] for c in fresh.values()], token)
        log.err(errs)
        for k in list(fresh):
            u = usage.get(k)
            if u and u["used"]:
                used[fresh[k]["repo"]] = u["reasons"]
                del fresh[k]
    elif not cfg["github_user"]:
        log.err(["config.github_user empty: already-used check skipped"])
    log.step("already_used(star/fork)", len(fresh) + len(used), len(fresh),
             "; ".join(f"{r}: {', '.join(why)}" for r, why in sorted(used.items())))

    # 9. Star-farming signals (flag only, never drop)
    flagged = 0
    for c in fresh.values():
        c["farm_signals"] = github.farm_signals(c, today)
        flagged += bool(c["farm_signals"])
    log.step("star_farming", len(fresh), len(fresh), f"{flagged} flagged (not dropped)")

    candidates = sorted(fresh.values(), key=lambda c: c["stars_today"], reverse=True)

    # 10. Persist state
    if not dry_run:
        spikes = set(over)
        seen = set(trending) | set(searched)
        wl = snapshot.update_watchlist(watchlist, seen, spikes, today,
                                       cfg["watchlist_stale_days"], cfg["watchlist_max"])
        snapshot.write_json(paths["watchlist"], wl)
        snapshot.save_snapshot(state_dir, today, {k: v for k, v in stars_now.items() if v is not None})
        snapshot.prune_snapshots(state_dir, today)

    status = "Success"
    if not trending and not searched:
        status = "Failed"
    elif log.errors:
        status = "Partial"
    if status != "Failed" and not candidates:
        status = "No picks"

    summary = {
        "date": today.isoformat(),
        "status": status,
        "sources": sources_used,
        "counts": {
            "candidates": len(pool),
            "over_threshold": len(over),
            "after_filters": len(fresh) + len(used),
            "already_used": len(used),
            "to_review": len(candidates),
        },
        "dropped": {"junk": junk, "repeat": skipped, "used": used},
        "errors": log.errors,
        "token": bool(token),
        "dry_run": dry_run,
    }
    if not dry_run:
        d = run_dir(state_dir, today)
        snapshot.write_json(os.path.join(d, "candidates.json"), candidates)
        snapshot.write_json(os.path.join(d, "log.json"), {"summary": summary, "steps": log.steps})
    return summary, candidates, log.steps


def record(state_dir, today, picks):
    """Persist Claude's final picks into suggested.json. picks: [{repo, team, stars_today, score, verdict, notion_url}]."""
    paths = _paths(state_dir)
    suggested = snapshot.read_json(paths["suggested"], {})
    for p in picks:
        entries = suggested.setdefault(p["repo"].lower(), [])
        entries = [e for e in entries if e["date"] != today.isoformat()]  # idempotent re-run
        entries.append({
            "date": today.isoformat(),
            "repo": p["repo"],
            "team": p.get("team"),
            "stars_today": p.get("stars_today"),
            "score": p.get("score"),
            "verdict": p.get("verdict"),
            "notion_url": p.get("notion_url"),
            "feedback": None,
        })
        suggested[p["repo"].lower()] = entries
    snapshot.write_json(paths["suggested"], suggested)
    snapshot.write_json(os.path.join(run_dir(state_dir, today), "picks.json"), picks)
    return len(picks)


def apply_feedback(state_dir, cfg, items):
    """
    items: [{repo, date, feedback}] read from Notion. Updates suggested.json, then recomputes
    weights from scratch (config weights + every recorded feedback) so re-runs never double count.
    """
    paths = _paths(state_dir)
    suggested = snapshot.read_json(paths["suggested"], {})
    changed = 0
    for it in items:
        for e in suggested.get(it["repo"].lower(), []):
            if e["date"] == it["date"] and e.get("feedback") != it.get("feedback"):
                e["feedback"] = it.get("feedback")
                changed += 1
    all_fb = [e for entries in suggested.values() for e in entries if e.get("feedback")]
    weights = update_weights(cfg["weights"], all_fb, cfg["weight_step"], cfg["weight_bounds"])
    snapshot.write_json(paths["suggested"], suggested)
    snapshot.write_json(paths["weights"], weights)
    return changed, weights


def effective_weights(state_dir, cfg):
    return snapshot.read_json(_paths(state_dir)["weights"], cfg["weights"])


def verify(state_dir, cfg, today, token, repos):
    """
    Slow checks on Claude's shortlist: star/fork + code search in the user's repos.
    Updates the run log so the Notion 'Already used' count stays complete.
    """
    usage, errors = github.check_used(cfg["github_user"], repos, token, code_search=True)
    used = {r: usage[r.lower()]["reasons"] for r in repos if usage.get(r.lower(), {}).get("used")}
    path = os.path.join(run_dir(state_dir, today), "log.json")
    data = snapshot.read_json(path, None)
    if data:
        data["steps"].append({
            "at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "step": "already_used(code search)", "in": len(repos), "out": len(repos) - len(used),
            "note": "; ".join(f"{r}: {', '.join(w)}" for r, w in sorted(used.items())),
        })
        s = data["summary"]
        s["counts"]["already_used"] += len(used)
        s["dropped"]["used"].update(used)
        s["errors"].extend(errors)
        if errors and s["status"] == "Success":
            s["status"] = "Partial"
        snapshot.write_json(path, data)
    return {"used": used, "clear": [r for r in repos if r not in used], "errors": errors}
