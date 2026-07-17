# Data source: Claude Code (/insights artifacts)

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

Joins both dirs by `session_id` (`has_facet` marks rows with assessments), prints coverage counts to stderr. If it exits with "No /insights data found", ask the user to run `/insights` in Claude Code, then retry — don't improvise another source.

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
