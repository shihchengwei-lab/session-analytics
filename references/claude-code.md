# Data source: Claude Code

Two sources, different strengths — pick by question, and say which one a number came from:

| Source | Needs | Has | Lacks |
|---|---|---|---|
| `/insights` artifacts (primary for quality questions) | user ran `/insights` recently | outcome/friction/satisfaction assessments (facets) | per-skill names; sessions since last run |
| Raw session logs (always available) | nothing | per-skill + per-subagent invocation names, always fresh | any quality assessment — outcomes are your inference only |

## /insights artifacts

Root: `$CLAUDE_CONFIG_DIR/usage-data` if that env var is set, else `~/.claude/usage-data`. Produced by the user running `/insights` inside Claude Code — precomputed, so reading them costs no LLM re-analysis.

| Subdirectory | Content | Nature |
|---|---|---|
| `session-meta/*.json` | Per-session mechanical stats | Computed by code; reliable |
| `facets/*.json` | Per-session LLM-written assessment | Model judgment, **not ground truth** |

`session-meta` covers more sessions than `facets`; sessions /insights never scanned are absent from both. Report coverage accordingly.

## Build the dataset

```
python <this skill's directory>/scripts/merge_facets.py <tmpdir>/merged.jsonl
```

Joins both dirs by `session_id` (`has_facet` marks rows with assessments), prints coverage counts to stderr. If it exits with "No /insights data found", fall back to the raw extractor below for mechanical questions; for quality questions (outcomes, friction) suggest running `/insights` — raw logs carry no assessments.

**Freshness**: artifacts only update when the user runs `/insights`. If the newest `start_time` in the data is much older than today, say so and suggest re-running `/insights` before a weekly review.

## Fields (observed 2026-07 — undocumented internals; a Claude Code update may change them. If files don't match, say so rather than forcing this schema.)

session-meta (every row):
`session_id, project_path, start_time, duration_minutes, user_message_count, assistant_message_count, tool_counts{name:count}, languages, git_commits, git_pushes, input_tokens, output_tokens, first_prompt, user_interruptions, user_response_times, tool_errors, tool_error_categories, uses_task_agent, uses_mcp, uses_web_search, uses_web_fetch, lines_added, lines_removed, files_modified, message_hours, user_message_timestamps`

facets (rows with `has_facet: true`):
- `outcome`: fully_achieved / mostly_achieved / partially_achieved / not_achieved / unclear_from_transcript
- `claude_helpfulness`: essential / very_helpful / moderately_helpful / slightly_helpful / unhelpful
- `session_type`: single_task / multi_task / iterative_refinement / exploration / quick_question
- `primary_success`: correct_code_edits / good_explanations / good_debugging / multi_file_changes / proactive_help / none
- `user_satisfaction_counts`: {happy/satisfied/likely_satisfied/dissatisfied/unclear: count}
- `friction_counts`: {wrong_approach/buggy_code/excessive_changes/misunderstood_request/user_rejected_action: count}
- `goal_categories`: free-form labels with many near-synonyms (bug_fix vs bug_fixing) — fuzzy-merge before counting; never treat as a fixed enum
- Text fields `underlying_goal, brief_summary, friction_detail` — keyword search here is the best way to find sessions about a theme

`duration_minutes` is the session's open span, not active typing time.

## Raw session logs (no-setup fallback + skill-level detail)

Root: `$CLAUDE_CONFIG_DIR/projects` (default `~/.claude/projects`) — `<munged-project-path>/<session-id>.jsonl`, one file per session, written live by Claude Code itself. No user action needed, always current. Subagent transcripts live in a sibling directory (`<session-id>/subagents/agent-*.jsonl`, newer versions) or as inline `isSidechain` lines (older); the extractor sums both into `sidechain_output_tokens` and never counts them as sessions.

```
python <this skill's directory>/scripts/extract_claude_raw.py <tmpdir>/raw.jsonl [days]
```

Windows by file mtime (default 7 days). Per session it emits: project, cwd, version, git branch, first/last timestamps, human message count, assistant turns, output tokens (deduped by API message id; `sidechain_output_tokens` carries subagent spend separately), `tool_counts`, **`skill_counts` (which skills, by name — /insights collapses these into one "Skill" total)**, `agent_types` (subagent names), `command_counts` (typed slash commands, incl. user-typed skill invocations), and the first few human inputs truncated. Sessions with zero human activity (title-gen, headless batch runs) are skipped and counted on stderr; if **every** file in the window is skipped, the extractor exits nonzero with a format-change hint instead of writing an empty dataset — relay that hint, don't report a quiet week.

Caveats (observed 2026-07, undocumented internals — if files don't match, say so rather than forcing this schema):

- `human_messages` counts plain typed prose only; typed slash invocations live in `command_counts`. A skill's true usage = `skill_counts` (model-invoked) + its `/name` entry in `command_counts` (user-typed) — judge hygiene on the sum. Loop/wakeup re-fires inflate the looped command's own count.
- Subagent (sidechain) traffic is excluded from conversation counts (messages, tools, skills); its token spend is tracked separately in `sidechain_output_tokens`. Total observed spend = `output_tokens` + `sidechain_output_tokens`.
- No outcome/friction/satisfaction fields exist here. Judgments about session quality from raw rows are your inference from the input samples — quote evidence, label as inference (same rules as the codex reference).
- `skill_counts` aggregated across the window vs. the installed-skill list (`~/.claude/skills/`, plugin skills, `~/.agents/skills/`) is the evidence base for skill-hygiene suggestions (disable/remove what's never invoked).
