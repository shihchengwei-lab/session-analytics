# session-analytics

An [Agent Skill](https://agentskills.io) for continuously improving how you work with AI coding agents. Each agent analyzes **its own tool's** local session logs over the last 7 days, answers your questions about them, and — in a weekly review — proposes evidence-tied workflow improvements, maintained as a small self-refactoring rules block in that tool's config. No data leaves your machine.

Why 7 days: month-long panoramas mix in old, already-corrected behavior; a rolling week keeps the signal about who you are *now*. Run it any time — a natural rhythm is spending leftover quota before your weekly usage reset.

## Two modes

- **Query**: "which sessions failed this week?", "my success rate", "compare my experiment runs" — or invoke bare for a one-screen weekly overview ending in grounded suggestions.
- **Weekly review**: the overview, plus evidence-tied changes on three fronts:
  - **Rules block** in the tool's config (`CLAUDE.md` / `AGENTS.md` / `GEMINI.md`): hard cap 10 one-line rules, each carrying its evidence and dates; every week the whole block is re-derived — keep / rewrite (friction recurred despite the rule) / merge (overlap) / retire (2 clean weeks = graduated) — so it refactors instead of accumulating
  - **Harness fixes beat prose rules**: friction a hook, env var, or permission entry can enforce mechanically gets a config-diff proposal instead of another rules line; a mechanism landing retires the prose rule it replaces
  - **Skill hygiene**: installed skills crossed against actual invocation counts (both model-invoked and user-typed); never-invoked ones flagged for disabling — with guards for newly installed skills and ambient plugins (statuslines, hooks, MCP) whose value isn't invocation-shaped
  - the agent shows a full diff and writes **only after you approve**; nothing outside the markers is ever touched

## Per-tool data sources

| Tool | Source | Cost |
|---|---|---|
| Claude Code (quality data) | `~/.claude/usage-data` (run `/insights` first) | precomputed — free to read |
| Claude Code (mechanical data) | `~/.claude/projects` raw logs via bundled extractor — no setup, always fresh, per-skill invocation counts | metadata + samples only |
| OpenAI Codex | `~/.codex/sessions/**.jsonl` via bundled extractor | metadata + samples only |
| Others | `references/generic.md` procedure | depends on what logs exist |

## Prerequisites

- Python 3 available to the agent
- Claude Code: outcome/friction assessments need `/insights` run at least once; everything mechanical works with zero setup. Codex: existing session logs

## Status

Early release. The analysis paths are tested against real data (Claude Code artifacts and raw logs; Codex logs at the data layer), and the skill-hygiene flow has been dry-run against 28 days of real sessions — its verdict guards each come from an actual false positive caught in that run. The weekly loop's multi-week behavior — rules being rewritten, merged, and retired across consecutive reviews — is specified but has not yet been exercised in the field, and the managed-block write path always requires your approval. Treat it as a v0 you watch, not an autopilot.

## Install

Clone straight into the cross-tool skills directory:

```
git clone https://github.com/shihchengwei-lab/session-analytics ~/.agents/skills/session-analytics
```

Or copy this folder manually. The SKILL.md format is an open standard (Claude Code, Codex CLI, Gemini CLI, Cursor, and others):

| Tool | User-level location |
|---|---|
| Cross-tool (Codex CLI, Gemini CLI, …) | `~/.agents/skills/session-analytics/` |
| Claude Code | `~/.claude/skills/session-analytics/` (or link from the above) |
| Gemini CLI | `~/.gemini/skills/session-analytics/` (also reads `~/.agents/skills/`) |

In Claude Code: `/session-analytics [question]`. In Codex CLI: `$session-analytics [question]`. Or plain language — "weekly review", "improve my workflow".

## Caveats

- Log formats are undocumented tool internals (schemas as observed 2026-07); tool updates may break extraction — the skill is instructed to say so rather than force stale schemas.
- Qualitative fields (outcomes, friction) are model judgments, not ground truth; where logs record none (Codex), judgments come from sampled evidence and are labeled as inference.
- Coverage is partial by design; every report states what it covers.
- Merged data contains your prompts and project paths — treat outputs as private.
