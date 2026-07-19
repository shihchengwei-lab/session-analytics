#!/usr/bin/env python3
"""PreToolUse gate: mechanically enforce the managed rules block at write time.

Closes the loop SKILL.md stage 5 step 6 leaves to prose: nothing there
physically stops a config write that skipped the validator. Installed as a
PreToolUse hook on Edit|Write, this script reconstructs the file content the
tool call would produce and runs the bundled validate_rules_block.py on
(current, proposed) before the write happens.

Decisions:
- file is not an agent config (CLAUDE.md / AGENTS.md / GEMINI.md), or the
  edit leaves the block byte-identical -> pass through untouched; editing
  one's own config outside the markers is none of this gate's business
- the block changes and the validator rejects (cap exceeded, markers
  damaged, outside-marker lines changed in the same call) -> deny, with
  the validator's reason
- the edit removes the entire block -> "ask": uninstalling is legitimate,
  but only the user may say so
- any internal error -> fail open; a broken gate must not lock the user
  out of their own config
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.stdin.reconfigure(encoding="utf-8")
sys.stdout.reconfigure(encoding="utf-8")

GUARDED = {"claude.md", "agents.md", "gemini.md"}
START = "<!-- session-analytics:rules START"
END = "<!-- session-analytics:rules END"
VALIDATOR = Path(__file__).resolve().parent / "validate_rules_block.py"


def decide(kind, reason):
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": kind,
            "permissionDecisionReason": reason,
        }
    }, ensure_ascii=False))
    sys.exit(0)


def block_text(text):
    """Content of the marker region, None when absent, "malformed" when the
    markers are not a clean single pair (compares unequal to everything, so
    a malformed file always falls through to the validator)."""
    lines = text.splitlines()
    starts = [i for i, l in enumerate(lines) if l.lstrip().startswith(START)]
    ends = [i for i, l in enumerate(lines) if l.lstrip().startswith(END)]
    if not starts and not ends:
        return None
    if len(starts) != 1 or len(ends) != 1 or ends[0] < starts[0]:
        return "malformed"
    return "\n".join(lines[starts[0]:ends[0] + 1])


def proposed_content(tool, tool_input, current):
    if tool == "Write":
        return tool_input.get("content")
    old, new = tool_input.get("old_string"), tool_input.get("new_string")
    if old is None or new is None:
        return None
    if old not in current:
        # The Edit tool matches across line-ending styles; mirror the CRLF
        # case so a guarded edit on a CRLF file is still reconstructed.
        old_crlf, new_crlf = old.replace("\n", "\r\n"), new.replace("\n", "\r\n")
        if "\r" not in old and old_crlf in current:
            old, new = old_crlf, new_crlf
        else:
            return None  # Edit itself will fail; nothing to guard
    return current.replace(old, new) if tool_input.get("replace_all") else current.replace(old, new, 1)


def main():
    payload = json.load(sys.stdin)
    if payload.get("tool_name") not in ("Edit", "Write"):
        sys.exit(0)
    tool_input = payload.get("tool_input") or {}
    path = Path(tool_input.get("file_path") or "")
    if path.name.lower() not in GUARDED:
        sys.exit(0)

    current = ""
    if path.is_file():
        with open(path, encoding="utf-8", errors="replace", newline="") as fh:
            current = fh.read()
    proposed = proposed_content(payload["tool_name"], tool_input, current)
    if proposed is None:
        sys.exit(0)
    if START not in current and START not in proposed:
        sys.exit(0)

    b_cur, b_new = block_text(current), block_text(proposed)
    if b_cur == b_new and b_cur != "malformed":
        sys.exit(0)
    if b_cur is not None and b_new is None:
        decide("ask", "此改動會把 session-analytics 規則區塊整個移除（解除安裝）。確定要移除嗎？")

    with tempfile.TemporaryDirectory() as td:
        cur_f, new_f = Path(td) / "current.md", Path(td) / "proposed.md"
        cur_f.write_bytes(current.encode("utf-8"))
        new_f.write_bytes(proposed.encode("utf-8"))
        res = subprocess.run(
            [sys.executable, str(VALIDATOR), str(cur_f), str(new_f)],
            capture_output=True, text=True, encoding="utf-8",
        )
    if res.returncode != 0:
        lines = [l for l in (res.stderr or "").strip().splitlines() if l.strip()]
        decide("deny", "session-analytics 規則區塊驗證失敗，改動已擋下："
               + (lines[-1] if lines else "validator error")
               + " 區塊外的修改請拆成另一次不碰區塊的編輯。")
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        sys.exit(0)  # fail-open
