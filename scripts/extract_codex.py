"""Extract Codex session logs into one compact JSONL for ad-hoc analysis.

Scans ~/.codex/sessions/**/rollout-*.jsonl, keeps sessions active in the
window (by file mtime; resumed sessions make path dates unreliable), and
emits one JSON line per session: session_meta subset, event-type counts,
last token_count payload, and the first user inputs (truncated). Whole
transcripts are never copied out - that is the cost boundary.

Usage:
    python extract_codex.py <output_path> [days]   # days defaults to 7

Coverage stats go to stderr so they never pollute the data stream.
"""
import json
import sys
import time
from collections import Counter
from pathlib import Path

SESSIONS = Path.home() / ".codex" / "sessions"
MAX_INPUTS = 5
TRUNC = 200


def walk(node, found):
    """Collect input_text strings and token_count payloads at any nesting depth."""
    if isinstance(node, dict):
        if node.get("type") == "input_text" and isinstance(node.get("text"), str):
            found["inputs"].append(node["text"])
        if node.get("type") == "token_count":
            # Observed shape: {"type":"event_msg","payload":{"type":"token_count","info":{...}}}
            found["token_count"] = node.get("info") or {}
        for v in node.values():
            walk(v, found)
    elif isinstance(node, list):
        for v in node:
            walk(v, found)


def extract(path):
    row = {"log_file": str(path)}
    counts = Counter()
    found = {"inputs": [], "token_count": None}
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                counts["unparsed_lines"] += 1
                continue
            t = obj.get("type", "?")
            counts[t] += 1
            if t == "session_meta":
                p = obj.get("payload", {})
                row.update({k: p.get(k) for k in ("session_id", "timestamp", "cwd", "originator", "cli_version")})
            walk(obj, found)
    row["event_counts"] = dict(counts)
    # Frameworks inject tag-shaped preambles (e.g. "<permissions instructions>")
    # as input_text; prefer human-looking inputs for the sample.
    human = [s for s in found["inputs"] if not s.lstrip().startswith("<")]
    row["user_inputs_sample"] = [s[:TRUNC] for s in (human or found["inputs"])[:MAX_INPUTS]]
    row["user_input_total"] = len(found["inputs"])
    row["last_token_count"] = found["token_count"]
    return row


def main():
    if len(sys.argv) < 2:
        sys.exit("usage: python extract_codex.py <output_path> [days]")
    days = float(sys.argv[2]) if len(sys.argv) > 2 else 7.0

    if not SESSIONS.is_dir():
        sys.exit(f"No Codex session logs found under {SESSIONS}.")

    cutoff = time.time() - days * 86400
    files = [p for p in SESSIONS.rglob("rollout-*.jsonl") if p.stat().st_mtime >= cutoff]
    if not files:
        sys.exit(f"{SESSIONS} has no sessions active in the last {days:g} days.")

    rows = sorted((extract(p) for p in files), key=lambda r: r.get("timestamp") or "")
    with open(sys.argv[1], "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"sessions: {len(rows)}  window: last {days:g} days (by mtime)", file=sys.stderr)


if __name__ == "__main__":
    main()
