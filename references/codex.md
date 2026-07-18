# Data source: OpenAI Codex (raw session logs)

Root: `~/.codex/sessions/YYYY/MM/DD/rollout-<timestamp>-<uuid>.jsonl` — one file per session, organized by start date. There is no precomputed assessment layer here (nothing like Claude's facets), so anything qualitative comes from you reading extracts — which spends your own tokens. The extractor below keeps that bounded.

Observed structure (2026-07, undocumented internals — if files don't match, say so rather than forcing this schema):

- First line: `{"type":"session_meta","payload":{session_id, timestamp, cwd, originator, cli_version, ...}}` — cheap, one line, everything needed for windowing and per-project grouping
- Remaining lines: typed events. Useful types: `input_text` (user inputs), `function_call` / `function_call_output` (tool usage), `agent_message` / `output_text` (agent replies), `token_count` (usage data under `info`, nested inside an `event_msg`; the same event also carries `rate_limits` — observed but not extracted), `reasoning`
- Sessions run to thousands of lines — **never read a whole file**; a resumed session's file mtime can be much newer than its path date, so window by mtime (last activity), not folder date

## Build the dataset

```
python <this skill's directory>/scripts/extract_codex.py <tmpdir>/merged.jsonl [days]
```

Windows by file mtime (default 7 days), and by whole files: a resumed session carries its pre-window activity into counts and samples. Per session it emits one JSON line: session_meta fields, event counts (nested payload types — `message:user` / `message:assistant`, `function_call`, `token_count`, `reasoning` — plus the top-level wrappers), last `token_count` payload, and the first few user inputs truncated. Input sampling is scoped to `role=user` messages (developer/system injections are excluded and tallied in `nonuser_input_total`). Coverage counts go to stderr; if no file yields a `session_meta`, a stderr warning flags a likely format change — mention it alongside any results.

The input sample prefers human-looking inputs: tag-shaped framework preambles (`<permissions instructions>` etc.) are skipped unless nothing else exists. Role scoping removes developer/system injections, but boilerplate injected **as the user role** (observed: `AGENTS.md` instructions, `## Memory` preambles) still slips through — every framework injects differently, and chasing them all in the extractor is a losing game. When judging user intent from samples, skim past anything that reads as boilerplate; it is not the user speaking. `user_input_total` counts every user-role text, so treat it as an upper bound on real user messages.

## What you can and cannot conclude

- Mechanical facts (session counts, projects, tool-call volume, user-input samples) — solid.
- Outcomes and friction are **not recorded**: judge them only from the sampled user inputs you actually see (e.g. repeated corrections, "that's wrong, again" patterns), quote the evidence, and label the judgment as your inference. No satisfaction scores exist here — don't invent them.
- If a question needs more than the samples provide, say what a deeper read would cost (opening N session files) and let the user decide.
