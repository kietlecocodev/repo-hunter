# Cloud routine prompt

Paste as the routine prompt (adjust paths if the routine checks repos out elsewhere):

```
Run the repo-hunter daily scan. Trigger = Scheduled.

The repos repo-hunter and repo-hunter-state are checked out in the working directory.
1. export REPO_HUNTER_STATE="$(pwd)/repo-hunter-state"
2. Read repo-hunter/skills/repo-hunter/SKILL.md and follow it exactly, using
   SKILL_DIR=repo-hunter/skills/repo-hunter. Notion ids are in $REPO_HUNTER_STATE/config.json.
3. GH_READ_TOKEN is set in the environment; do not print it.
4. Always finish with a Daily Runs page in Notion and a state commit pushed to repo-hunter-state,
   even if some steps fail.
```
