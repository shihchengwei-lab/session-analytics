# Data source: other tools

No reference exists for this tool yet. In order:

1. **Find the logs.** Check the tool's docs/config for a local session-history location (common: a dot-directory in the user's home, e.g. `~/.gemini/history`). Ask the user if unclear. Confirm what a session record actually contains before promising analysis — list one file, peek at its first lines, and describe honestly what's measurable.
2. **Build `merged.jsonl` yourself**: one JSON line per session in the window with whatever is mechanically extractable (start time, project/cwd, message counts, tool calls, user-input samples truncated). Follow the codex reference as a template: metadata first, never whole transcripts, window by last activity, coverage counts to stderr.
3. **No logs at all?** Say so plainly. Improvement mode can still run in *prospective* form: maintain the managed rules block from what the user reports and what you observe in the current session — but label the evidence accordingly ("user-reported", "this session"), and don't fabricate statistics about sessions you cannot see.

Qualitative judgments (outcome, friction) that the logs don't record are your inference from samples — quote the evidence and label them as inference, same as the codex rules.
