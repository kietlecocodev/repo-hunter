# Repo Hunter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship `repo-hunter` as a public Claude Code plugin + marketplace that finds GitHub repos gaining ≥200 stars/day, filters them deterministically, and lets Claude classify/compare/log them to Notion daily.

**Architecture:** Deterministic Python (stdlib only) does collection (Trending + Search API + snapshot delta, OSS Insight fallback), filtering, repeat rule and "already used" check, writing `runs/<date>/candidates.json` + `log.json`. `SKILL.md` drives Claude for judgment work (classify, similar-repo agents, risk, Notion writes) and calls `record` / `feedback` subcommands to persist history. Personal config + state live in a separate private repo (`repo-hunter-state`), so the plugin repo is safe to publish.

**Tech Stack:** Python 3.10+ stdlib (`urllib`, `re`, `json`, `unittest`, `zoneinfo`), GitHub REST/GraphQL, Notion MCP, Claude Code cloud routine.

---

### Task 1: Plugin skeleton + marketplace
**Files:** Create `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `README.md`, `LICENSE`, `.gitignore`.
- [ ] Write manifests following `~/mind-vault/.claude-plugin/*` pattern.
- [ ] `claude plugin validate .` passes.
- [ ] Commit.

### Task 2: HTTP + config helpers
**Files:** Create `skills/repo-hunter/scripts/rh/net.py`, `rh/config.py`. Test: `tests/test_config.py`.
- [ ] Test: `load_config(dir)` merges `config.json` over defaults; missing file → defaults.
- [ ] Implement; run `python3 -m unittest discover -s tests` → PASS. Commit.

### Task 3: Sources (Trending parse, Search API, OSS Insight)
**Files:** Create `rh/sources.py`. Test: `tests/test_sources.py`, fixture `tests/fixtures/trending.html` (trimmed real page).
- [ ] Test: `parse_trending(html)` returns repo, description, language, stars, forks, stars_today for each article; handles missing language.
- [ ] Test: `build_search_queries(date)` returns the two queries from spec §5.
- [ ] Implement; tests PASS. Commit.

### Task 4: Snapshot + watchlist
**Files:** Create `rh/snapshot.py`. Test: `tests/test_snapshot.py`.
- [ ] Tests: `previous_snapshot` picks latest date < today; `daily_delta` divides by day gap; `update_watchlist` adds, prunes stale, caps size.
- [ ] Implement; PASS. Commit.

### Task 5: Rules (threshold, junk, repeat, weights)
**Files:** Create `rh/rules.py`. Test: `tests/test_rules.py`.
- [ ] Tests: threshold 200 boundary; junk reasons (archived, fork, no license, blocklist name/desc); repeat rule (new / skip in cooldown / resuggest at 2× / resuggest on major release / 👎 never); weight update clamps 0.5–2.0.
- [ ] Implement; PASS. Commit.

### Task 6: Already-used check + star-farming sample
**Files:** Create `rh/used.py`. Test: `tests/test_used.py` (pure helpers only: `classify_usage`, `farm_ratio`).
- [ ] Implement network calls (starred, forks→parent, code search) + pure helpers; PASS. Commit.

### Task 7: Pipeline CLI
**Files:** Create `skills/repo-hunter/scripts/repo_hunter.py`. Test: `tests/test_pipeline.py` (collect with stubbed sources).
- [ ] Subcommands: `collect`, `record`, `feedback`, `init-state`. Each step appends to `log.json`.
- [ ] Test end-to-end with monkeypatched fetchers → candidates + log counts correct. Commit.

### Task 8: SKILL.md + references
**Files:** Create `skills/repo-hunter/SKILL.md`, `references/notion-schema.md`, `references/routine-prompt.md`, `references/comparison-agent.md`.
- [ ] Workflow steps 1–11 from spec, Notion write format, dry-run mode. Commit.

### Task 9: Publish
- [ ] Create private `kietlecocodev/repo-hunter-state` with `config.json` (Notion IDs) + empty state.
- [ ] Make `kietlecocodev/repo-hunter` public; push.
- [ ] `claude plugin marketplace add kietlecocodev/repo-hunter` + install locally; live `collect --dry-run` smoke test.
