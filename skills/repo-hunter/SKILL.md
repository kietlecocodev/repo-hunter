---
name: repo-hunter
description: Daily GitHub scout. Finds repos gaining ≥200 stars in a day (GitHub Trending + Search API + star snapshots), keeps the ones that boost product / design / dev team productivity (product first), skips repos already starred / forked / integrated or suggested recently, compares each pick with existing similar repos (strengths, weaknesses, 5 reasons to use, 5 reasons not to) and logs every run and suggestion to Notion. Use when the user says "/repo-hunter", "repo hunter", "tìm repo hay", "repo trending hôm nay", "github hôm nay có gì", or when a scheduled routine invokes it.
---

# Repo Hunter

Deterministic work (collecting, star math, filters, repeat rule, already-used check) is done by
`scripts/repo_hunter.py`. You do the judgment work: classify, compare, assess risk, write Notion.
**Never invent numbers** — every star count, date and count you write comes from the script's JSON or
from a GitHub API response you fetched in this run.

Output language for everything written to Notion or shown to the user: **Vietnamese**. Keep product
terms in English when the team uses them (repo, star, fork, agent, skill, prompt, CLI, SDK…).

## 0. Setup (each run)

```
SKILL_DIR = this skill's base directory (shown when the skill loads)
SCRIPT    = $SKILL_DIR/scripts/repo_hunter.py
STATE     = $REPO_HUNTER_STATE, else ~/.repo-hunter   (a clone of the user's PRIVATE state repo)
```

- `STATE/config.json` must exist. If not, stop and tell the user to follow `references/setup.md`.
- Token: the script reads `GH_READ_TOKEN` / `GITHUB_TOKEN` / `GH_TOKEN`. If none is set but `gh` is logged
  in, export `GH_READ_TOKEN=$(gh auth token)` for the commands below. No token → still run; report the
  reduced checks.
- Arguments: `--dry-run` → run everything but write nothing (no Notion, no state, no commit); print the
  final suggestions in chat instead. `--date YYYY-MM-DD` → pass through to the script.
- If `STATE` is a git repo: `git -C $STATE pull --rebase` first.

Keep a running **action log** (list of `HH:MM — step — result`) from here on. It becomes the body of
the Daily Runs page (step 8). Log every step, including failures and skipped steps.

## 1. Apply yesterday's feedback (learn)

Read `config.notion.suggestions_data_source`. Query rows whose `Feedback` is set and `Date` is within the
last 30 days. Write `[{"repo": "...", "date": "YYYY-MM-DD", "feedback": "👍|👎|Đã thử"}]` to a temp file, then:

```bash
python3 $SCRIPT --state-dir $STATE feedback --items /tmp/rh-feedback.json
```

It returns the new team weights. Notion unreachable → log it and continue with `weights` from step 2.

## 2. Collect

```bash
python3 $SCRIPT --state-dir $STATE collect --full > /tmp/rh-collect.json
```

Read `summary` (status, sources, counts, dropped, errors), `weights`, `max_picks`, `notion`, and
`candidates` (sorted by `stars_today`). Each candidate has: `repo, description, language, stars, forks,
stars_today, stars_today_source (trending|snapshot), license, topics, created_at, pushed_at, homepage,
resuggest, repeat_reason, farm_signals`.

- `status == "Failed"` → skip to step 8 and log a Failed run.
- No candidates → skip to step 8 with status `No picks`.

## 3. Classify & score (you)

For each candidate, read its README (`gh api repos/{repo}/readme -H "Accept: application/vnd.github.raw"`,
first ~150 lines is enough) plus description/topics. Decide:

- `team`: **product** (PM / research / analytics / docs / roadmap / user feedback / AI agents that do
  product work / no-code builders / prototyping) · **design** (UI, design systems, Figma, assets,
  motion, design-to-code, taste/art-direction) · **dev** (coding agents, frameworks, infra, devtools,
  testing) · **none** (unrelated: finance models, games, personal collections, regional-only apps, pure
  research code with no tool, jailbreak/prompt dumps, lists).
- `fit` 0.0–1.0: how much it would speed up that team's daily work at a small mobile/AI product company.
- `score = round(log10(stars_today) × weights[team] × fit, 3)`.

Drop `none` and `fit < 0.4`. Keep the top `max_picks` by score. Log the cut list with one-line reasons.

## 4. Already-used agent

Spawn **one** subagent (general-purpose) with this brief:

> Check whether GitHub user `<config.github_user>` already uses any of these repos: `<shortlist>`.
> 1. Run `python3 <SCRIPT> --state-dir <STATE> verify --repos <comma list>` (star, fork, code search
>    for "owner/name" in the user's repos).
> 2. For each repo still "clear", find its published package / CLI / skill names from its README
>    (npm, PyPI, brew, `claude plugin install …`, skill folder name) and run `gh search code
>    "<package name>" --owner <user> --limit 5`. Also check `gh api users/<user>/repos --paginate
>    --jq '.[].name'` for a repo with the same name (manual copy).
> 3. Return JSON: `{"used": {"owner/name": ["reason", ...]}, "clear": [...], "notes": [...]}`.
> Do not guess: only mark used when you saw the evidence; quote it.

Drop every repo in `used` from the shortlist. Backfill from the next-best scored candidates (run the
agent again on the backfill only) so you still have up to `max_picks`. Log both.

## 5. Similar-repo comparison agents (parallel)

For each remaining pick, spawn one subagent **in the same message** (they run concurrently). Brief:
see `references/comparison-agent.md` (copy it, filling in the repo and its candidate JSON).
Each returns: similar repos (2–4, with stars and last push date), strengths, weaknesses,
5 reasons to use, 5 reasons not to use, verdict (`Nên thử` / `Theo dõi` / `Bỏ qua`), sources.

An agent fails → keep the pick, write "Chưa so sánh được" in the comparison, set run status `Partial`.

## 6. Risk (you)

`Risk` = **Cao** if any: no license or non-OSI license, needs broad system permissions / runs arbitrary
code on your machine with network access, asks for credentials of third-party accounts, `farm_signals`
non-empty, single maintainer and created < 30 days ago. **Trung bình** if: needs API keys, AGPL/GPL (copyleft
affects product use), last push > 90 days, created < 90 days. Else **Thấp**. Write the reasons.

Verify every factual claim in the comparison (claim-validator style): if you cannot point to a source
fetched in this run, drop or soften the claim.

## 7. Write suggestions to Notion

Use the Notion MCP tools available in this session (names vary by connector: `notion-create-pages`,
`notion-fetch`, `notion-query-data-sources`…). Fetch the data sources first to confirm property names.
Create the Daily Runs page first (step 8 fields can be updated at the end) so suggestions can relate to it.

One page per pick in `notion.suggestions_data_source`:

| Property | Value |
|---|---|
| Repo | `owner/name` |
| URL | `https://github.com/owner/name` |
| Date | run date |
| Run | the Daily Runs page |
| Team | Product / Design / Dev |
| Stars today | `stars_today` (integer) |
| Total stars | `stars` |
| Score | score |
| Re-suggest | `resuggest` |
| Similar repos | `a/b (12.3k★), c/d (4.1k★)` |
| Verdict | from step 5 |
| License | SPDX or "Không có" |
| Risk | Thấp / Trung bình / Cao |
| Summary | 1–2 câu: repo làm gì, tại sao đáng chú ý hôm nay |

Page body: follow `references/notion-templates.md` → "Suggestion page".

Then record the picks (skip in dry-run):

```bash
python3 $SCRIPT --state-dir $STATE record --picks /tmp/rh-picks.json
# [{"repo","team","stars_today","score","verdict","notion_url"}]
```

## 8. Daily Runs log (always, even on failure)

One page in `notion.runs_data_source`, title = run date:
`Date`, `Status` (summary.status, downgraded to `Partial` if any later step failed), `Trigger`
(`Scheduled` when started by a routine, else `Manual`), `Source` (summary.sources), `Candidates`,
`Over 200`, `After filters`, `Already used` (collect + step 4), `Suggested`, `Errors` (joined, ≤ 1500
chars), `Commit` (step 9). Page body: `references/notion-templates.md` → "Run page", including the
full action log and the script's step table from `STATE/state/runs/<date>/log.json`.

Notion unavailable → write the same content to `STATE/state/runs/<date>/report.md` and say so.

## 9. Commit state

If `STATE` is a git repo and not dry-run:

```bash
git -C $STATE add -A && git -C $STATE commit -m "chore(state): run <date>" && git -C $STATE push
```

Retry push once after `pull --rebase`. Put the commit URL in the Daily Runs `Commit` property.

## 10. Reply

Short Vietnamese summary in chat: status, counts funnel (lấy về → ≥200 → sau lọc → đã dùng → suggest),
the picks (team, stars today, verdict, one line each), Notion link, and any errors/skipped checks.

## Rules

- Never suggest a repo the user already starred/forked/integrated.
- Respect the repeat rule result from the script; don't re-add dropped repos.
- Product-team repos first when scores tie.
- No picks is a valid outcome — log it, don't lower the bar.
- Never write tokens or private repo contents to Notion; repo names where integration was found are OK
  (the Notion page is private) but no code excerpts.
