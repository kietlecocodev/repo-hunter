# repo-hunter

Daily GitHub scout for **product, design and dev teams** (product first), as a Claude Code plugin.

Every day it:

1. Collects repos gaining stars fast: **GitHub Trending** (`stars today`) + **GitHub Search API**
   (new fast-growing repos and active popular ones) + its own **daily star snapshots** to compute real
   per-day deltas for repos that are not on Trending.
2. Keeps repos with **≥ 200 stars in a day**, drops archived / forks / lists / tutorials / blocklisted topics.
3. **Repeat rule:** a repo suggested in the last 14 days only comes back if its daily stars doubled or it
   shipped a new major release; 👎 means never again.
4. **Already used?** Skips repos you starred, forked or reference in your own repos (code search +
   package-name check by an agent).
5. Claude classifies each repo (product / design / dev), scores it with your learned team weights and
   keeps the top 6.
6. One agent per pick finds **similar existing repos** and writes strengths, weaknesses,
   **5 reasons to use / 5 reasons not to**, a verdict and a risk level.
7. Writes everything to **Notion** (a *Daily Runs* log of every action + a *Suggestions* database
   with a 👍/👎 column that tunes future weights) and commits state to your private state repo.

## Install

```
/plugin install repo-hunter --marketplace kietlecocodev/repo-hunter
```

or, on older Claude Code:

```
/plugin marketplace add kietlecocodev/repo-hunter
/plugin install repo-hunter@repo-hunter
```

Then follow [`skills/repo-hunter/references/setup.md`](skills/repo-hunter/references/setup.md):
private state repo, Notion databases, GitHub token, and the 10:00 (GMT+7) cloud routine.

## Use

```
/repo-hunter --dry-run   # full scan, nothing written
/repo-hunter             # full run
```

## Layout

```
.claude-plugin/              plugin + marketplace manifests
skills/repo-hunter/
  SKILL.md                   workflow Claude follows
  references/                setup, routine prompt, comparison-agent brief, Notion templates
  scripts/repo_hunter.py     CLI: collect | verify | record | feedback | weights | init-state
  scripts/rh/                stdlib-only Python: sources, snapshot, rules, github, pipeline
tests/                       python3 -m unittest discover -s tests -t tests
docs/superpowers/            design spec + implementation plan
```

No personal data lives in this repo: config, snapshots and suggestion history are in your private
`repo-hunter-state` repo (`$REPO_HUNTER_STATE`, default `~/.repo-hunter`).

## Notes

- Python 3.10+, standard library only.
- Without a GitHub token it still works, with fewer checks (no code search; watchlist refresh capped).
- The stargazers list endpoint is not readable (checked 2026-11-02), so fake-star detection uses cheap
  signals (forks/stars ratio, age vs stars) and only raises the risk level.
- OSS Insight's trending ranking is unavailable since 2026-03-01, so it is not used as a fallback.

MIT
