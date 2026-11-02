#!/usr/bin/env python3
"""repo-hunter CLI.

  collect   [--state-dir D] [--date YYYY-MM-DD] [--dry-run]   run deterministic pipeline, print JSON
  verify    --repos a/b,c/d                                  code-search shortlist in user's repos
  record    --picks FILE                                     save final picks to suggested.json
  feedback  --items FILE                                     apply 👍/👎 from Notion, recompute weights
  weights                                                    print effective team weights
  init-state --github-user U [--runs-ds ID] [--suggestions-ds ID]   create config.json in state dir

State dir: --state-dir, else $REPO_HUNTER_STATE, else ~/.repo-hunter
GitHub token (optional but recommended): $GH_READ_TOKEN / $GITHUB_TOKEN / $GH_TOKEN
"""
import argparse
import datetime as dt
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rh import net, pipeline, snapshot  # noqa: E402
from rh.config import load_config  # noqa: E402


def _today(cfg, override):
    if override:
        return dt.date.fromisoformat(override)
    try:
        from zoneinfo import ZoneInfo
        return dt.datetime.now(ZoneInfo(cfg["timezone"])).date()
    except Exception:
        return (dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=7)).date()


def _load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _print(obj):
    json.dump(obj, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")


def main(argv=None):
    ap = argparse.ArgumentParser(description="repo-hunter pipeline")
    ap.add_argument("--state-dir", default=os.environ.get("REPO_HUNTER_STATE", os.path.expanduser("~/.repo-hunter")))
    ap.add_argument("--date")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("collect")
    c.add_argument("--dry-run", action="store_true")
    c.add_argument("--full", action="store_true", help="also print candidates and steps")
    v = sub.add_parser("verify")
    v.add_argument("--repos", required=True, help="comma-separated owner/name list")
    r = sub.add_parser("record")
    r.add_argument("--picks", required=True)
    f = sub.add_parser("feedback")
    f.add_argument("--items", required=True)
    sub.add_parser("weights")
    i = sub.add_parser("init-state")
    i.add_argument("--github-user", required=True)
    i.add_argument("--runs-ds", default="")
    i.add_argument("--suggestions-ds", default="")
    a = ap.parse_args(argv)

    state = os.path.expanduser(a.state_dir)
    cfg = load_config(state)
    today = _today(cfg, a.date)

    if a.cmd == "init-state":
        path = os.path.join(state, "config.json")
        if os.path.exists(path):
            sys.exit(f"{path} already exists; edit it instead")
        snapshot.write_json(path, {
            "github_user": a.github_user,
            "notion": {"runs_data_source": a.runs_ds, "suggestions_data_source": a.suggestions_ds},
        })
        _print({"created": path})
    elif a.cmd == "collect":
        summary, candidates, steps = pipeline.collect(state, cfg, today, net.github_token(), dry_run=a.dry_run)
        out = {"summary": summary, "weights": pipeline.effective_weights(state, cfg),
               "max_picks": cfg["max_picks"], "notion": cfg["notion"],
               "run_dir": pipeline.run_dir(state, today)}
        if a.full or a.dry_run:
            out.update({"candidates": candidates, "steps": steps})
        _print(out)
    elif a.cmd == "verify":
        repos = [x.strip() for x in a.repos.split(",") if x.strip()]
        _print(pipeline.verify(state, cfg, today, net.github_token(), repos))
    elif a.cmd == "record":
        _print({"recorded": pipeline.record(state, today, _load(a.picks))})
    elif a.cmd == "feedback":
        changed, weights = pipeline.apply_feedback(state, cfg, _load(a.items))
        _print({"changed": changed, "weights": weights})
    elif a.cmd == "weights":
        _print(pipeline.effective_weights(state, cfg))


if __name__ == "__main__":
    main()
