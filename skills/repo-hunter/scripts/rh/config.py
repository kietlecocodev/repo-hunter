"""Config: defaults overridden by <state_dir>/config.json."""
import copy
import json
import os

DEFAULTS = {
    "github_user": "",
    "timezone": "Asia/Ho_Chi_Minh",
    "threshold": 200,
    # "" = all languages page
    "languages": ["", "python", "typescript", "javascript", "go", "rust", "swift", "kotlin", "unknown"],
    "search": {"new_repo_days": 30, "new_repo_min_stars": 300, "active_min_stars": 1000, "per_query": 300},
    "watchlist_max": 2000,
    "watchlist_stale_days": 30,
    "cooldown_days": 14,
    "resuggest_multiplier": 2.0,
    "max_picks": 6,
    "require_license": False,  # missing license raises Risk instead of dropping
    "weights": {"product": 1.5, "design": 1.2, "dev": 1.0},
    "weight_step": 0.05,
    "weight_bounds": [0.5, 2.0],
    "blocklist_name": [
        "awesome", "tutorial", "tutorials", "course", "courses", "interview", "roadmap",
        "leetcode", "cheatsheet", "crypto", "airdrop", "game", "games", "wallpaper",
    ],
    "blocklist_desc": [
        "curated list", "list of awesome", "airdrop", "free robux", "cracked", "hack tool",
        "interview questions", "course materials",
    ],
    "notion": {"runs_data_source": "", "suggestions_data_source": ""},
}


def _merge(base, over):
    out = copy.deepcopy(base)
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


def load_config(state_dir):
    path = os.path.join(state_dir, "config.json")
    over = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            over = json.load(f)
    return _merge(DEFAULTS, over)
