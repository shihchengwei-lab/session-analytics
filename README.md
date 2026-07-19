# session-analytics

**English** · [繁體中文](README.zh-TW.md)

An [Agent Skill](https://agentskills.io) for continuously improving how you work with AI coding agents — a **self-optimizing harness skill**: each agent analyzes **its own tool's** local session logs over the last 7 days, reinforces the paths you actually use, prunes the ones you don't, and re-validates its own past advice across model changes — so your setup keeps improving without accumulating. Reads local data only and uploads nothing; analysis samples flow through your agent's model context — the same trust boundary as every other session with that agent.

Why 7 days: month-long panoramas mix in old, already-corrected behavior; a rolling week keeps the signal about who you are *now*. Run it any time — a natural rhythm is spending leftover quota before your weekly usage reset.

## Two modes

- **Query**: "which sessions failed this week?", "my success rate", "compare my experiment runs" — or invoke bare for a one-screen weekly overview ending in grounded suggestions. Query mode reports; it changes nothing.
- **Weekly review**: the overview, plus evidence-tied changes on three fronts:
  - **Rules block** in the tool's config (`CLAUDE.md` / `AGENTS.md` / `GEMINI.md`): a fenced block between comment markers, hard-capped at 10 one-line rules (3 on first install), each carrying its evidence and dates; every week the whole block is re-derived — keep / rewrite (friction recurred despite the rule) / merge (overlap) / retire (2 clean weeks = graduated) — so it refactors instead of accumulating. A model switch devalues old evidence: rules confirmed only under the previous model are re-validated, not auto-kept
  - **Harness fixes beat prose rules**: friction a hook, env var, or permission entry can enforce mechanically gets a config-diff proposal instead of another rules line; a mechanism landing retires the prose rule it replaces. Proposals to *build* something new must climb the wheel ladder first: adopt → configure → extract the needed piece → copy the design smaller → build from scratch only with a stated reason
  - **Skill hygiene, both directions**: installed skills crossed against actual invocation counts (both model-invoked and user-typed). Hot paths get friction-removal proposals (sharper triggers, permission allowlists); never-invoked ones are flagged for disabling — with guards for newly installed skills and ambient plugins (statuslines, hooks, MCP) whose value isn't invocation-shaped

  The rules block is the only file the skill ever edits, and three layers keep that write honest: every proposal must pass the mechanical validator (marker boundary byte-exact, rule caps) before you're even shown the diff; the agent writes **only after you approve**; and if the optional write-time hook is installed, the validator runs once more at the moment of writing, so a malformed write is denied even when the workflow skipped it. Removing the whole block (uninstalling) is allowed but requires an explicit confirmation. Hand-written rules inside the markers are preserved verbatim; nothing outside the markers is ever touched.

## What a report looks like

From a real run (project names genericized):

```
Window: 2026-07-11 → 2026-07-18 · thin sample: 5 sessions, 3 with quality assessments
  (raw logs show 10 sessions in this window — /insights artifacts lag; re-run /insights for full coverage)
Outcomes (assessed only): 2 fully_achieved · 1 mostly_achieved
Top frictions: wrong_approach ×4 · buggy_code ×1 · excessive_changes ×1
Volume: ~100 h open-session span (not active time) · 855k output tokens
        top projects: game-project, dotfiles, guardrails-lab
Notable: no failed or stalled session in the assessed set this week
Suggestions:
  1. All 4 wrong_approach marks sit in game-project (07-11 + 07-15 — both sessions still landed):
     the agent gets there after rework. Try opening those sessions with a one-line goal +
     constraints statement; check next week whether the count drops.
  2. Thin sample (5 sessions) — widen the window or re-run /insights before reading trends.
```

(Reports are written in whatever language you work in with your agent; this one is kept as produced. The features to notice: thin samples confess themselves, coverage comes first, and every suggestion carries its evidence.)

## Repository layout

| Path | Role |
|---|---|
| `SKILL.md` | The instructions the agent follows — five stages: route the request, build the dataset, analyze, report, apply (weekly only) |
| `references/claude-code.md`, `codex.md`, `generic.md` | Per-tool guides: where the logs live, what each field means, which questions the data can and cannot answer |
| `scripts/extract_claude_raw.py` | Compresses raw Claude Code session logs (`~/.claude/projects`) into one JSON line per session |
| `scripts/extract_codex.py` | Same for Codex (`~/.codex/sessions`) |
| `scripts/merge_facets.py` | Joins Claude Code `/insights` artifacts (session metadata + quality assessments) into one dataset |
| `scripts/validate_rules_block.py` | Mechanical gate for the rules block: marker boundary byte-exact, rule caps, enforced by exit code |
| `scripts/guard_rules_block.py` | Optional write-time hook: intercepts agent edits to the config files and runs the validator before the write lands |
| `tests/` | 29 stdlib-only tests on synthetic logs and configs — extractors, validator, and hook |

All scripts are Python standard library only — no dependencies, no network access.

## Data sources

| Tool | Source | Cost |
|---|---|---|
| Claude Code (quality data) | `~/.claude/usage-data` (run `/insights` first) | precomputed — free to read |
| Claude Code (mechanical data) | `~/.claude/projects` raw logs via bundled extractor — no setup, always fresh, per-skill invocation counts | metadata + samples only |
| OpenAI Codex | `~/.codex/sessions/**.jsonl` via bundled extractor | metadata + samples only |
| Others | `references/generic.md` procedure | depends on what logs exist |

Per session, the extractors record: timestamps and duration, project path and git branch, model names, tool/skill/subagent/slash-command invocation counts, output-token totals (main conversation and subagents separately), and up to 5 of your prompts truncated to 200 characters each — that sample is the only piece of your own writing in the dataset. Whole transcripts are never copied out; that is the cost boundary.

If logs exist but nothing in them is recognizable (the signature of a log-format change after a tool update), the extractors say so loudly — the Claude Code one refuses to write a dataset at all; the Codex one emits what is still usable and warns on stderr — so a schema break reads as "extraction broke", never as "you had no sessions this week".

## Privacy & cost

- Everything runs locally; the scripts open no network connections. The analysis itself is performed by your agent, so the aggregates and prompt samples it examines enter the model context and travel to the model provider like any other conversation content — the same trust boundary as the rest of your sessions, no new one and no smaller one.
- Dataset files live in a temp directory and contain your prompts and project paths — treat them as private; don't paste bulk rows anywhere public.
- A typical run reads compact datasets, not transcripts, and costs on the order of a normal conversation turn. The one expensive operation — deep-reading a single session's full log — requires your explicit opt-in after being told it costs real tokens.

## Prerequisites

- Python 3 available to the agent
- Claude Code: outcome/friction assessments need `/insights` run at least once; everything mechanical works with zero setup. Codex: existing session logs

## Non-goals

The bundled data layer is a deliberately minimal, zero-dependency fallback — not a product. This skill will not grow: new agent parsers, a session database or search index, a dashboard/UI, or token-cost accounting. Mature local tools already do those well (below); this skill's actual job is the decision layer — turning session evidence into a small number of bounded, reversible, user-approved harness changes.

## Prior art & interoperability

- [AgentsView](https://github.com/kenn-io/agentsview) — local-first session search/analytics across 20+ agents (SQLite, skill-usage trends, session archetypes). If it already indexes your sessions, prefer it as the mechanical data source: build the stage-2 dataset from its stats output per `references/generic.md` (field mapping untested — state coverage honestly).
- [ccusage](https://github.com/ccusage/ccusage) — token/usage reports across a dozen agent CLIs; same story for volume numbers.
- Retrospective-style skills ([glebis/claude-skills](https://github.com/glebis/claude-skills), [session-retrospective](https://github.com/accidentalrebel/claude-skill-session-retrospective), [reflect](https://github.com/hansvangent/reflect-skill-claude)) — per-session or per-day review loops that update skills or `CLAUDE.md`. This skill differs in window (rolling week), evidence base (mechanical + assessed outcomes), and in maintaining a capped, self-refactoring rules block behind a mechanical write guard.

## Status

Early release. The analysis paths are tested against real data (Claude Code artifacts and raw logs; Codex logs at the data layer), and the skill-hygiene flow has been dry-run against 28 days of real sessions — its verdict guards each come from an actual false positive caught in that run. The write-time hook has been exercised live: a marker-breaking edit was denied in a real session. The weekly loop's multi-week behavior — rules being rewritten, merged, and retired across consecutive reviews — is specified but has not yet been exercised in the field, and the managed-block write path always requires your approval. Treat it as a v0 you watch, not an autopilot.

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

In Claude Code: `/session-analytics [question]`. In Codex CLI: `$session-analytics [question]`. Or plain language — "weekly review", "improve my workflow". Nothing runs unless invoked; the two optional additions below change that, which is why they're opt-in.

### Optional: write-time guard hook (Claude Code)

Enforces the rules-block contract mechanically on every agent file edit: non-config files pass through after a filename check; edits that touch the block re-run the validator and are denied if malformed; removing the whole block asks for confirmation. Adds roughly 0.1–0.3 s of Python startup per edit and is fail-open — if the hook itself crashes, the edit proceeds, so a broken gate can never lock you out of your own config. Add to `~/.claude/settings.json` hooks, with the path adjusted to your install location:

```json
"PreToolUse": [
  {
    "matcher": "Edit|Write",
    "hooks": [
      {
        "type": "command",
        "command": "python /absolute/path/to/session-analytics/scripts/guard_rules_block.py",
        "timeout": 10
      }
    ]
  }
]
```

Other tools have no standard hook system; there the validator still runs inside the workflow, just without this mechanical backstop.

### Optional: weekly schedule

Use your tool's scheduler (e.g. Claude Code desktop's scheduled tasks) to invoke the skill weekly with "weekly review". Instruct the scheduled run to stop at report + proposals — approval happens with you present, never unattended.

## Development

Tests run on synthetic logs and configs, stdlib-only: `python -m pytest tests/` (or `python -m unittest discover tests`). Covers the extractors, the validator, and the hook. No CI is set up — run them yourself after changes.

## Caveats

- Log formats are undocumented tool internals (schemas as observed 2026-07); tool updates may break extraction — the skill is instructed to say so rather than force stale schemas.
- Qualitative fields (outcomes, friction) are model judgments, not ground truth; where logs record none (Codex), judgments come from sampled evidence and are labeled as inference.
- Coverage is partial by design; every report states what it covers.
- Skill triggering (outside an explicit `/session-analytics` invocation) is the agent's judgment call on the trigger description — not a mechanical guarantee.
- The guard hook covers the two standard edit tools; an agent writing through raw shell commands bypasses it. It's there to catch mistakes, not to stop a determined bypass.
