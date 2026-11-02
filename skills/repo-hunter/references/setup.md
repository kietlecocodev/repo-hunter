# Setup

## 1. Install the plugin (any machine)

```
/plugin install repo-hunter --marketplace kietlecocodev/repo-hunter
```

## 2. Private state repo (once per user)

State (snapshots, suggestion history, weights) and personal config live in a **private** repo so the
plugin repo can stay public.

```bash
gh repo create <you>/repo-hunter-state --private --clone ~/.repo-hunter
python3 <plugin>/skills/repo-hunter/scripts/repo_hunter.py --state-dir ~/.repo-hunter \
  init-state --github-user <you> --runs-ds <Daily Runs data source id> --suggestions-ds <Suggestions data source id>
git -C ~/.repo-hunter add -A && git -C ~/.repo-hunter commit -m "init" && git -C ~/.repo-hunter push -u origin HEAD
```

On another machine: `gh repo clone <you>/repo-hunter-state ~/.repo-hunter`.

Any key from `scripts/rh/config.py` `DEFAULTS` can be overridden in `config.json`
(threshold, languages, cooldown_days, resuggest_multiplier, max_picks, weights, blocklists…).

## 3. Notion (once per user)

Create a page "Repo Hunter" with two databases. Ask Claude: "create the repo-hunter Notion databases
from references/setup.md" — schemas:

**Daily Runs**
`Run` title · `Date` date · `Status` select(Success, Partial, Failed, No picks) · `Trigger` select(Scheduled, Manual)
· `Source` multi-select(Trending, Search API, Snapshot delta) · `Candidates` number · `Over 200` number
· `After filters` number · `Already used` number · `Suggested` number · `Errors` text · `Commit` url

**Suggestions**
`Repo` title · `URL` url · `Date` date · `Run` relation → Daily Runs (two-way "Suggestions") · `Team` select(Product, Design, Dev)
· `Stars today` number · `Total stars` number · `Score` number · `Re-suggest` checkbox · `Similar repos` text
· `Verdict` select(Nên thử, Theo dõi, Bỏ qua) · `License` text · `Risk` select(Thấp, Trung bình, Cao)
· `Summary` text · `Feedback` select(👍, 👎, Đã thử)

Put both `collection://…` ids into `config.json` → `notion`.

## 4. GitHub token

Fine-grained PAT, read-only: *Metadata*, *Contents* (all your repos, for code search), *Starring*.
Locally `gh auth token` works too. Cloud routine: set it as env `GH_READ_TOKEN`.

## 5. Daily schedule (cloud routine, 10:00 GMT+7)

In Claude Code run `/schedule` and create a routine:

- Cron: `0 3 * * *` (UTC) = 10:00 Asia/Ho_Chi_Minh
- Repositories: `<you>/repo-hunter` and `<you>/repo-hunter-state` (state needs push access)
- Connectors: Notion (with access to the "Repo Hunter" page)
- Env: `GH_READ_TOKEN=<PAT>`
- Prompt: see `routine-prompt.md`

## 6. Manual run / test

```
/repo-hunter --dry-run      # nothing written
/repo-hunter                # full run, Trigger = Manual
```
