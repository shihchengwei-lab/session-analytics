"""Extract raw Claude Code session logs into one compact JSONL for ad-hoc analysis.

Fallback / complement to /insights artifacts: works with zero user setup
(no /insights run needed) and records per-skill invocation names, which
/insights tool_counts collapses into a single "Skill" total. Scans
$CLAUDE_CONFIG_DIR/projects (default ~/.claude/projects), keeps sessions
active in the window (by file mtime), and emits one JSON line per session.
Whole transcripts are never copied out - that is the cost boundary.

Usage:
    python extract_claude_raw.py <output_path> [days]   # days defaults to 7

Coverage stats go to stderr so they never pollute the data stream.
"""
import json
import os
import re
import sys
import time
from collections import Counter
from pathlib import Path

PROJECTS = Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude") / "projects"
MAX_INPUTS = 5
TRUNC = 200
# Typed slash commands (incl. user-typed skill invocations) arrive as wrapped
# user messages, NOT as Skill tool calls - without counting these, a skill the
# user always types by hand looks "never invoked".
COMMAND_RE = re.compile(r"<command-name>(/[\w:.-]+)</command-name>")


def extract(path):
    row = {"log_file": str(path), "session_id": path.stem, "project_dir": path.parent.name}
    tool_counts = Counter()
    skill_counts = Counter()
    agent_types = Counter()
    command_counts = Counter()
    inputs = []
    first_ts = last_ts = None
    output_tokens = 0
    sidechain_output_tokens = 0
    seen_msg_ids = set()
    seen_sidechain_ids = set()
    models = set()
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                tool_counts["__unparsed_lines__"] += 1
                continue
            if obj.get("isSidechain"):
                # Subagent traffic stays out of conversation counts, but its
                # tokens are real spend - track them in their own field so
                # agent-heavy sessions aren't undercounted.
                m = (obj.get("message") or {}) if obj.get("type") == "assistant" else {}
                mid = m.get("id")
                if mid and mid not in seen_sidechain_ids:
                    seen_sidechain_ids.add(mid)
                    sidechain_output_tokens += (m.get("usage") or {}).get("output_tokens") or 0
                continue
            t = obj.get("type")
            ts = obj.get("timestamp")
            if ts and t in ("user", "assistant"):
                first_ts = first_ts or ts
                last_ts = ts
            if t == "user":
                msg = obj.get("message") or {}
                content = msg.get("content")
                if isinstance(content, str):  # tool_results are lists; skip them
                    cmd = COMMAND_RE.search(content)
                    if cmd:
                        command_counts[cmd.group(1)] += 1
                    # Real human prose has origin.kind == "human".
                    elif (obj.get("origin") or {}).get("kind") == "human":
                        inputs.append(content)
                    if cmd or (obj.get("origin") or {}).get("kind") == "human":
                        for k in ("cwd", "version", "gitBranch"):
                            row.setdefault(k, obj.get(k))
            elif t == "assistant":
                msg = obj.get("message") or {}
                if msg.get("model"):
                    models.add(msg["model"])
                # One API response spans several lines sharing message.id with
                # identical usage - dedupe or output_tokens multiply-counts.
                mid = msg.get("id")
                if mid and mid not in seen_msg_ids:
                    seen_msg_ids.add(mid)
                    output_tokens += (msg.get("usage") or {}).get("output_tokens") or 0
                for c in msg.get("content") or []:
                    if isinstance(c, dict) and c.get("type") == "tool_use":
                        name = c.get("name", "?")
                        tool_counts[name] += 1
                        inp = c.get("input") or {}
                        if name == "Skill" and inp.get("skill"):
                            skill_counts[inp["skill"]] += 1
                        elif name == "Agent" and inp.get("subagent_type"):
                            agent_types[inp["subagent_type"]] += 1
    # Newer format stores subagent transcripts as separate files under
    # <session-id>/subagents/ instead of inline isSidechain lines (both
    # handled; same spend either way).
    subdir = path.parent / path.stem / "subagents"
    if subdir.is_dir():
        for sub in subdir.glob("*.jsonl"):
            with open(sub, encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    try:
                        obj = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if obj.get("type") == "assistant":
                        m = obj.get("message") or {}
                        mid = m.get("id")
                        if mid and mid not in seen_sidechain_ids:
                            seen_sidechain_ids.add(mid)
                            sidechain_output_tokens += (m.get("usage") or {}).get("output_tokens") or 0

    if not inputs and not command_counts:
        return None  # warmup/internal session (title gen etc.), not a user session
    minutes = None
    if first_ts and last_ts:
        try:
            from datetime import datetime
            span = datetime.fromisoformat(last_ts.rstrip("Z")) - datetime.fromisoformat(first_ts.rstrip("Z"))
            minutes = round(span.total_seconds() / 60, 1)
        except ValueError:
            pass
    # Frameworks inject tag-shaped wrappers (e.g. "<command-name>") as user
    # content; prefer human-looking inputs for the sample.
    human = [s for s in inputs if not s.lstrip().startswith("<")]
    row.update({
        "first_ts": first_ts, "last_ts": last_ts, "duration_minutes": minutes,
        "human_messages": len(inputs), "assistant_turns": len(seen_msg_ids),
        "output_tokens": output_tokens, "sidechain_output_tokens": sidechain_output_tokens,
        "models": sorted(models),
        "tool_counts": dict(tool_counts), "skill_counts": dict(skill_counts),
        "agent_types": dict(agent_types), "command_counts": dict(command_counts),
        "user_inputs_sample": [s[:TRUNC] for s in (human or inputs)[:MAX_INPUTS]],
    })
    return row


def main():
    if len(sys.argv) < 2:
        sys.exit("usage: python extract_claude_raw.py <output_path> [days]")
    days = float(sys.argv[2]) if len(sys.argv) > 2 else 7.0

    if not PROJECTS.is_dir():
        sys.exit(f"No Claude Code session logs found under {PROJECTS}.")

    cutoff = time.time() - days * 86400
    files = [p for p in PROJECTS.glob("*/*.jsonl") if p.stat().st_mtime >= cutoff]
    if not files:
        sys.exit(f"{PROJECTS} has no sessions active in the last {days:g} days.")

    rows, skipped = [], 0
    for p in files:
        r = extract(p)
        if r is None:
            skipped += 1
        else:
            rows.append(r)
    if not rows:
        # Files exist but none contained recognizable human activity - the
        # signature of a log-format change. Fail loudly; an empty dataset
        # downstream reads as "no sessions this week", which misleads.
        sys.exit(
            f"All {skipped} session files in the window were skipped (no recognizable "
            "human activity). If you expected sessions here, the log format may have "
            "changed - report that instead of analyzing an empty dataset."
        )
    rows.sort(key=lambda r: r.get("first_ts") or "")
    with open(sys.argv[1], "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"sessions: {len(rows)}  skipped (no human input): {skipped}  "
          f"window: last {days:g} days (by mtime)", file=sys.stderr)


if __name__ == "__main__":
    main()
