# Comparison agent brief

Copy this brief into one subagent per pick. Fill `<…>`.

---

You are evaluating the GitHub repo **<owner/name>** for a small mobile/AI product company whose
**<team>** team might adopt it. Candidate data from today's scan (authoritative numbers, do not change):

```json
<candidate JSON from collect>
```

Tasks:

1. **Understand it.** Read the README (`gh api repos/<owner/name>/readme -H "Accept: application/vnd.github.raw"`),
   latest release (`gh api repos/<owner/name>/releases/latest`), open issues count and recent issues titles
   (`gh api "repos/<owner/name>/issues?state=open&per_page=10"`).
2. **Find 2–4 similar repos that existed before it** — same job-to-be-done, ideally >1k stars. Use
   `gh search repos "<keywords>" --sort stars --limit 15` with 2–3 keyword sets taken from its README and
   topics, plus your own knowledge (then verify each with `gh api repos/<x>`). For each similar repo
   record: full name, stars, `pushed_at` date, license, one-line positioning.
3. **Compare.** Strengths and weaknesses of <owner/name> **relative to those repos** (features, setup
   effort, ecosystem/integrations, maturity, maintenance activity, license, performance claims — mark
   claims that come only from the repo's own README as "theo README").
4. **5 lý do nên dùng** and **5 lý do không nên dùng**, specific to a <team> team (not generic).
5. **Verdict**: `Nên thử` (clear gain over what exists, low adoption cost), `Theo dõi` (promising but
   immature / unclear gain), `Bỏ qua` (no gain over existing tools or too risky).

Rules: every number must come from an API response you fetched; cite sources (URLs). If you can't find
similar repos, say so — do not invent any. Write in Vietnamese, keep product/tech terms in English.

Return exactly:

```json
{
  "repo": "<owner/name>",
  "similar": [{"repo": "", "stars": 0, "pushed_at": "", "license": "", "positioning": ""}],
  "strengths": [""],
  "weaknesses": [""],
  "reasons_to_use": ["", "", "", "", ""],
  "reasons_not_to_use": ["", "", "", "", ""],
  "verdict": "Nên thử|Theo dõi|Bỏ qua",
  "verdict_reason": "",
  "sources": [""]
}
```
