---
name: session-analytics
description: Weekly self-improvement loop for AI coding agents, plus ad-hoc usage analytics. Each agent analyzes its OWN tool's local session logs over the last 7 days (Claude Code via /insights artifacts, Codex via ~/.codex/sessions, others via their logs), reports success rates, friction patterns, stalled sessions, tool/token usage — and in a weekly review proposes evidence-tied workflow improvements: a small capped rules block in the tool's config (diff shown, user approves, block self-refactors instead of accumulating), mechanical harness fixes (hooks/env/permissions) preferred over prose rules, and skill/config hygiene (installed-but-never-invoked skills flagged for disabling). Trigger on "weekly review", "improve my workflow", "分析我的 session／使用紀錄", "which sessions failed", "my success rate", "compare my experiment runs", "哪些 skill 沒在用／停用沒用的 skill", or bare invocation (= 7-day overview). Reads local data only. Not for regenerating the official /insights report, or deep-reading one full transcript (expensive — see Cost rules).
---

# Session analytics & weekly workflow improvement

Two jobs, one skill:

1. **Query mode** — answer the user's analytical questions about their recent sessions with this tool.
2. **Improvement mode (weekly review)** — analyze the last 7 days and propose evidence-tied changes on three fronts: a small managed rules block in this tool's config, mechanical harness fixes where the tool supports them, and skill/config hygiene — so the collaboration actually changes week over week instead of repeating the same frictions.

The window is a rolling **7 days** by default. Why 7: older sessions mix in behavior that has already been corrected, which pollutes the signal; a week is recent enough to act on. The user can name any other range per question.

## Which data am I reading?

Each agent analyzes **its own tool's** logs — Claude Code data stays meaningful to Claude Code sessions, Codex data to Codex. Before touching data, read the reference for the tool you are running in:

- Claude Code → `references/claude-code.md` (precomputed /insights artifacts for quality data; raw session logs for freshness + per-skill detail)
- OpenAI Codex → `references/codex.md` (raw session JSONL; metadata-first, bundled extractor)
- Any other tool → `references/generic.md`

Each reference defines where logs live and how to build `merged.jsonl` — a one-line-per-session dataset in your temp directory. Everything below is source-agnostic.

## Query mode

1. **Build the dataset** per your tool's reference (re-run each time; data may have been refreshed).
2. **Query** — write a small Python script against `merged.jsonl` for the user's question; print aggregates plus a handful of example rows only. Don't load the whole file into context (hundreds of KB; you need answers, not raw text). Write query code to a file and run it (inline `python -c` breaks on Windows backslash paths); set `PYTHONUTF8=1` when output may contain non-ASCII (Windows consoles default to legacy codepages).
3. **Report** — numbers plus concrete example sessions (date + first-prompt snippet + project path tail, so the user can recognize the session).

### No question given

Invoked bare, produce the standard overview of the window instead of asking what they want — a user who typed the skill name already told you. Roughly one screen:

1. Coverage: window dates, session count, how many carry quality assessments (thin-sample rule applies)
2. Outcome distribution
3. Top friction types
4. Volume: active time, output tokens, most-worked projects
5. Most notable failed or stalled session, one line
6. Improvement suggestions per "Suggestions ride on evidence" — or one line saying the sample is too thin

Close by inviting a specific follow-up. Don't pad empty sections.

## Improvement mode — the weekly loop

Trigger: "weekly review" / "週回顧" / "improve my workflow" / the user asks to turn analysis into lasting changes. Typical rhythm: once a week, e.g. spending leftover quota before a usage reset — but any time works.

1. Produce the bare overview (above) for the last 7 days.
2. Derive suggestions (rules below).
3. Open the **managed rules block** in this tool's user-level config — Claude Code: `~/.claude/CLAUDE.md`; Codex: `~/.codex/AGENTS.md`; Gemini CLI: `~/.gemini/GEMINI.md`; otherwise ask the user where agent instructions live. No block yet → this is a first run; propose one (max 3 rules — rules must earn their place, don't fill the cap on day one).
4. Re-derive the **entire block** against this week's evidence — every existing rule gets a verdict:
   - **keep** — its target friction would plausibly recur without it; refresh the confirmed date
   - **rewrite** — the friction recurred *despite* the rule: the rule failed, so change it (sharper wording, different mechanism); never add a second rule for the same problem
   - **merge** — two rules overlap; combine into the stronger one
   - **retire** — target friction absent for 2 consecutive reviews → "graduated" (internalized or obsolete). If retiring regresses, next review sees the recurrence and brings a rewritten rule back — the loop self-corrects, so retire without fear.
5. Before adding any rule, check whether the user's config or skills **already cover it**. If yes and the friction still recurred, the existing rule is what failed — propose rewriting that one (with approval) or flag the conflict; don't duplicate it in the block.
6. Show the full old→new block diff, every change annotated with why + the evidence behind it. **Write only after the user approves. Never touch anything outside the markers.**

### Harness fixes beat prose rules

Before a friction becomes a rules-block line, ask: **can the harness enforce this mechanically?** A prose rule taxes every session's context and relies on the model remembering; a hook, env var, or permission entry fires without either. If the tool supports it (Claude Code: hooks/env/permissions in `settings.json`; other tools: check their config docs), propose the mechanical fix instead — exact config diff, user approves, same as rules. An existing prose rule whose job a new mechanism now does → retire it in the same review, crediting the mechanism. Examples: recurring "forgot `PYTHONUTF8`" → set it once in env; a repeatedly-fumbled risky action → a PreToolUse guard; "always do X after Y" → a hook, not a sentence.

### Skill & config hygiene

Part of each weekly review. Cross the **installed-skill inventory** (the running agent sees its own available-skills list; disk locations per the tool's reference) against **actual invocation counts** for the window — for Claude Code, `skill_counts` from the raw extractor; widen to ~28 days (`[days]` arg) before judging, one quiet week proves little. Then flag, for the user to decide:

- **Never invoked in the wide window** → candidate to disable/remove. Name the count and window. Low frequency alone is not waste — a situational skill (incident tooling, rare formats) earns its keep when needed; state what it's for and let the user judge.
- **Overlapping triggers** — two skills claiming the same job → suggest consolidating into the better one.

Three verdict guards (each learned from a real false positive):

- **Count both invocation paths** — model-invoked and user-typed (Claude Code: `skill_counts` + `/name` in `command_counts`). A skill the user only ever types by hand looks dead on tool-call counts alone.
- **Installation age gates the verdict** — a skill younger than the window has no evidence either way; skip it.
- **Ambient plugins can't be judged by invocation counts** — statuslines, hooks, MCP servers work without ever being "called" as a skill; name the mechanism instead of flagging them.

Record each decision as one comment line inside the block markers (`<!-- hygiene: kept X, removed Y — 2026-07-18 -->`, latest line replaces the previous) and don't re-raise a declined suggestion for 4 weeks — hygiene that nags gets turned off.

## Managed rules block

```
<!-- session-analytics:rules START (weekly-reviewed; max 10; edits outside markers are never touched) -->
- R1 [since 2026-07-18 | confirmed 2026-07-18] One-line behavioral rule. (evidence: 2 sessions 7/11+7/15, unverified-claim rework)
<!-- session-analytics:rules END -->
```

- **Hard cap 10 rules.** The block is loaded into every future session — each line taxes every session's context, so terseness is the feature. At the cap, adding requires a merge or retirement in the same diff.
- One line per rule, phrased as a behavior change, with since/confirmed dates and its evidence in parentheses.
- Rules the skill didn't write (hand-added inside the block) are preserved verbatim unless the user approves changing them.

## Reporting rules

- **Default window: last 7 days**, unless the question names another range. State the window used. Fewer than ~10 sessions → lead with "thin sample: N sessions", deliver what the data supports, ask before widening. Never widen silently — a "weekly report" that quietly covers a month misleads.
- **State coverage first**: sessions covered, and how many carry quality assessments. "X% of assessed sessions failed" ≠ "X% of all sessions failed".
- **Every number comes from computation you just ran** — no recall, no extrapolation. Can't compute it → say so.
- **Separate "the data says" from "I infer"**. Precomputed assessments are themselves a model's judgment: citable, fallible. Causal readings are inference; label them.
- Cross-check narratives against mechanical fields — "planning consumed the whole session" reads differently at `duration_minutes: 2` (truncated) than 60 (genuine stall).
- **Suggestions ride on evidence**: in the bare overview and for diagnostic questions, close with 1–3 improvement suggestions; each names the sessions/counts it rests on and proposes something the user can change (a prompt habit, a config rule, a workflow step). Purely factual questions get no unsolicited advice. Never emit advice the shown data doesn't support — "too thin to advise" is a respectable conclusion.

## Cost rules

Prefer precomputed artifacts; where only raw logs exist, extract metadata and small samples, never full transcripts. Do not deep-read a single session's full log without the user explicitly opting in after being told it costs real tokens. Analysis stops at `merged.jsonl`.

## Privacy

`merged.jsonl` contains the user's prompts and project paths. Treat outputs as private; don't paste bulk rows into anything that leaves the machine without the user asking.
