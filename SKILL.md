---
name: session-analytics
description: Weekly self-improvement loop for AI coding agents, plus ad-hoc usage analytics. Each agent analyzes its OWN tool's local session logs over the last 7 days (Claude Code via /insights artifacts, Codex via ~/.codex/sessions, others via their logs), reports success rates, friction patterns, stalled sessions, tool/token usage — and in a weekly review proposes evidence-tied workflow improvements: a small capped rules block in the tool's config (diff shown, user approves, block self-refactors instead of accumulating), mechanical harness fixes (hooks/env/permissions) preferred over prose rules, and skill/config hygiene both directions (hot paths reinforced, installed-but-never-invoked skills flagged for disabling; rule evidence re-validated across model changes). Trigger on "weekly review", "improve my workflow", "分析我的 session／使用紀錄", "which sessions failed", "my success rate", "compare my experiment runs", "哪些 skill 沒在用／停用沒用的 skill", or bare invocation (= 7-day overview). Reads local data only. Not for regenerating the official /insights report, or deep-reading one full transcript (expensive — see Cost rules).
---

# Session analytics & weekly workflow improvement

**Positioning: a self-optimizing harness skill.** Read the last 7 days of real usage, then work both directions: paths the user actually uses get reinforced (friction removed, access smoothed), paths they don't get pruned (flagged for retirement) — and the skill's own past advice is re-validated the same way, so the setup keeps improving across model changes instead of accumulating stale rules.

## Pipeline

Every invocation walks the same stages in order. Query mode stops after stage 4; weekly review runs all five.

| Stage | Input | Action | Output |
|---|---|---|---|
| 1 Route | the user's request | pick mode, window, tool reference | mode + reference file |
| 2 Build | tool's local logs | run bundled extractor(s) | dataset file(s) in temp dir |
| 3 Analyze | dataset file(s) | small Python scripts | computed numbers |
| 4 Report | computed numbers | fill the output templates | user-facing report |
| 5 Apply *(weekly only)* | report + current config | propose rules / harness fixes / hygiene | approved config diffs |

## Stage 1 — Route

**Mode**, by what the user said:

- a specific analytical question → **query mode** (stages 2–4)
- "weekly review" / "週回顧" / "improve my workflow" / asks to turn analysis into lasting changes → **weekly review** (stages 2–5)
- bare invocation, no question → **query mode with the bare-overview template** — a user who typed the skill name already told you what they want; don't ask.

**Window**: rolling 7 days default. Why 7: older sessions mix in behavior that has already been corrected, which pollutes the signal; a week is recent enough to act on. The user can name any other range; state whichever window you used. Hygiene verdicts (stage 5) widen to ~28 days — one quiet week proves little.

**Tool reference** — each agent analyzes its **own tool's** logs; read yours before touching data:

- Claude Code → `references/claude-code.md` (/insights artifacts for quality data; raw session logs for freshness + per-skill detail)
- OpenAI Codex → `references/codex.md` (raw session JSONL; metadata-first, bundled extractor)
- any other tool → `references/generic.md`

## Stage 2 — Build the dataset (input contract)

Run the extractor(s) named in your reference into your temp directory. Re-run on every invocation — data may have been refreshed. Each dataset is one JSON line per session.

**Common core** — every source provides these concepts; field names differ:

| Concept | Claude /insights | Claude raw | Codex |
|---|---|---|---|
| session id | `session_id` | `session_id` | `session_id` |
| start time | `start_time` | `first_ts` | `timestamp` |
| project | `project_path` | `cwd` / `project_dir` | `cwd` |
| duration | `duration_minutes` | `duration_minutes` | — (derive if needed) |
| user input sample | `first_prompt` | `user_inputs_sample` | `user_inputs_sample` |
| tool usage | `tool_counts` | `tool_counts` | `event_counts` |
| output tokens | `output_tokens` | `output_tokens` | `last_token_count` |

**Source-specific extras** decide which questions each source can answer:

- quality assessments (`outcome`, `friction_counts`, satisfaction — model judgments, not ground truth) → **/insights only**
- `skill_counts` (model-invoked skills), `command_counts` (user-typed slash commands), `models` (which model served each session), `sidechain_output_tokens` (subagent spend — `output_tokens` alone is main-conversation only and undercounts agent-heavy sessions) → **Claude raw only**
- if a question needs a field your source lacks, say so instead of improvising.

**Checks before analyzing**: report the extractor's stderr coverage counts; check freshness (newest start time vs today — stale /insights artifacts → say so and suggest re-running `/insights`). Windows select whole sessions by last activity — a resumed session carries pre-window activity into its counts; when one long-lived session dominates volume, say so.

## Stage 3 — Analyze

- Write query code to a file and run it — inline `python -c` breaks on Windows backslash paths; set `PYTHONUTF8=1` when output may contain non-ASCII.
- Print aggregates plus a handful of example rows only. Never load the whole dataset into context — hundreds of KB; you need answers, not raw text. Analysis stops at the dataset files.
- Weekly review additionally computes: outcome distribution (assessed rows only), friction counts, volume, the hygiene cross (installed inventory × `skill_counts` + `command_counts`), and whether the window spans a model change (`models` field, or dates).

## Stage 4 — Report (output contract)

**Bare overview** — exactly this skeleton, roughly one screen; skip an empty line entirely rather than padding it:

```
Window: <dates> · <N> sessions, <M> with quality assessments
Outcomes: <distribution — or "no assessments in window; run /insights">
Top frictions: <top 2-3 types with counts>
Volume: <open-session span (NOT active time — sessions idle open) · output tokens · most-worked projects>
Notable: <one line — the most instructive failed or stalled session>
Suggestions: <1-3 per the evidence rule below — or "sample too thin to advise">
```

Every template line is conditional on its data existing (stage 2 extras): no quality assessments → the Outcomes/frictions lines say so instead of guessing; no duration → drop the span figure. Degrade by omission-with-a-note, never by filling in.

Close by inviting a specific follow-up. **Query answers**: the computed numbers, then example rows as `date · project-path tail · first-prompt snippet` so the user can recognize the session.

Rules for every report:

- **Coverage first, thin samples flagged**: fewer than ~10 sessions → lead with "thin sample: N sessions"; ask before widening the window, never widen silently. "X% of assessed sessions" ≠ "X% of all sessions".
- **Every number comes from computation you just ran** — no recall, no extrapolation. Can't compute it → say so.
- **Separate "the data says" from "I infer"**: precomputed assessments are a model's judgment — citable, fallible; causal readings are inference, label them. Cross-check narratives against mechanical fields ("planning consumed the session" reads differently at `duration_minutes: 2` than 60).
- **Suggestions ride on evidence**: 1–3 per report, each naming the sessions/counts it rests on and proposing something the user can change. Purely factual questions get no unsolicited advice; "too thin to advise" is a respectable conclusion.

## Stage 5 — Apply (weekly review only)

1. Open the **managed rules block** in this tool's user-level config — Claude Code: `~/.claude/CLAUDE.md`; Codex: `~/.codex/AGENTS.md`; Gemini CLI: `~/.gemini/GEMINI.md`; otherwise ask where agent instructions live. No block yet → first run: propose one with max 3 rules — rules must earn their place.
2. Re-derive the **entire block** against this week's evidence — every existing rule gets a verdict:
   - **keep** — its target friction would plausibly recur without it; refresh the confirmed date
   - **rewrite** — the friction recurred *despite* the rule: the rule failed, change it (sharper wording, different mechanism); never add a second rule for the same problem
   - **merge** — two rules overlap; combine into the stronger one
   - **retire** — target friction absent for 2 consecutive reviews → graduated. If retiring regresses, the next review brings a rewritten rule back — the loop self-corrects, so retire without fear.

   **Model changes devalue old evidence**: a rule confirmed only under a previous model is not auto-kept — re-validate against post-switch sessions; friction the new model doesn't exhibit retires early. This keeps the block from fossilizing, and is why every rule carries dates and evidence: an unattributed rule can't be re-validated and rots in place.
3. Before adding any rule, check whether the user's config or skills **already cover it** — if yes and the friction still recurred, the existing rule is what failed: propose rewriting that one (with approval) or flag the conflict; don't duplicate it in the block.
4. **Harness fixes beat prose rules**: a friction the harness can enforce mechanically (Claude Code: hooks/env/permissions in `settings.json`; other tools per their docs) gets a config-diff proposal instead of a rules line — a prose rule taxes every session's context and relies on the model remembering; a hook does neither. A mechanism landing retires the prose rule it replaces. Examples: recurring "forgot `PYTHONUTF8`" → set it in env; a repeatedly-fumbled risky action → a PreToolUse guard.

   **Adopt before build.** When a proposal would *create* something new — a skill, a hook script, a tool — inventory outward before writing line one: an installed-but-idle skill may already do it (the hygiene cross has the data); the tool may ship it built-in; the ecosystem likely has it — search the web/marketplace first. It's a ladder, not a binary: adopt as-is → configure → extract just the piece you need from a bigger project (license permitting) → copy its design and write a smaller version → build from scratch only when every rung above fails, and say why. Searching spends tokens — climb the ladder only when the proposal is a build.
5. **Skill & config hygiene — bolden the used, prune the unused**: cross the installed-skill inventory (the agent sees its own available-skills list; disk locations per your reference) against invocation counts, both paths summed (`skill_counts` + `/name` in `command_counts` — a skill only ever typed by hand looks dead on tool calls alone). Then, user decides:
   - **heavily used** → reinforce: remove friction on the hot path — sharper trigger description, permission allowlist (Claude Code ships `fewer-permission-prompts` for this — invoke it, don't reimplement)
   - **never invoked in the wide window** → candidate to disable/remove; name the count and window. Guards: a skill younger than the window has no evidence either way — skip it; ambient plugins (statuslines, hooks, MCP servers) work without being "called" — never judge them by invocation counts; a situational skill may earn its keep rarely — state what it's for, let the user judge.
   - **overlapping triggers** → suggest consolidating into the better one.

   Record decisions as one comment line inside the block markers (`<!-- hygiene: kept X, removed Y — 2026-07-18 -->`, latest replaces previous); don't re-raise a declined suggestion for 4 weeks — hygiene that nags gets turned off.
6. Write the proposed config to a temp file and run `python <this skill's directory>/scripts/validate_rules_block.py <current_file> <proposed_file>` — it mechanically enforces the marker boundary and the rule caps (10, or 3 on a first run) — the block's own "harness fix beats prose rule". A failure means fix the proposal, not show it. Then show the full old→new diff, each change annotated with why + evidence. **Write only after the user approves. Never touch anything outside the markers.**

### Managed rules block format

```
<!-- session-analytics:rules START (weekly-reviewed; max 10; edits outside markers are never touched) -->
- R1 [since 2026-07-18 | confirmed 2026-07-18] One-line behavioral rule. (evidence: 2 sessions 7/11+7/15, unverified-claim rework)
<!-- session-analytics:rules END -->
```

- **Hard cap 10 rules** — the block loads into every future session; each line taxes every session's context, so terseness is the feature. At the cap, adding requires a merge or retirement in the same diff.
- One line per rule, phrased as a behavior change, with since/confirmed dates and evidence in parentheses.
- Rules the skill didn't write (hand-added inside the markers) are preserved verbatim unless the user approves changing them.

## Cost & privacy

Prefer precomputed artifacts; where only raw logs exist, extract metadata and small samples, never full transcripts. Do not deep-read a single session's full log without the user explicitly opting in after being told it costs real tokens. Dataset files contain the user's prompts and project paths — treat outputs as private; don't paste bulk rows into anything that leaves the machine without the user asking. Analysis samples do enter this agent's model context — the same trust boundary as the rest of the session; nothing else leaves the machine.
