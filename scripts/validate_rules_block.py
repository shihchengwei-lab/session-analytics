"""Validate the session-analytics managed rules block - the mechanical half
of the block's contract, enforced by code instead of prose.

Static mode:  python validate_rules_block.py <config_file>
Edit mode:    python validate_rules_block.py <old_file> <new_file>

Errors (exit 1):
- marker pair missing, duplicated, or out of order
- more than 10 rule lines between the markers
- edit mode: any line outside the marker region changed, byte-exact
  (first-run block insertion into an unchanged file is allowed, capped
  at 3 rules per the spec)

Warnings (exit 0): rule lines not matching the documented format - the spec
preserves hand-added rules verbatim, so format drift must not hard-fail.

Run this in edit mode on (current file, proposed file) BEFORE showing the
diff for approval; a validator failure means the proposal is malformed and
must be fixed, not shown.
"""
import re
import sys
from pathlib import Path

START = "<!-- session-analytics:rules START"
END = "<!-- session-analytics:rules END"
MAX_RULES = 10
RULE_RE = re.compile(
    r"^- R\d+ \[since \d{4}-\d{2}-\d{2} \| confirmed \d{4}-\d{2}-\d{2}\] .+\(evidence: .+\)\s*$"
)


def read_exact_lines(path):
    """Lines with their original endings intact - newline="" disables Python's
    universal-newline translation, so a whole-file CRLF/LF rewrite outside the
    markers cannot slip through the untouched-content comparison."""
    with open(path, encoding="utf-8", newline="") as fh:
        return fh.read().splitlines(keepends=True)


def split_block(lines, label):
    """Return (pre, block, post); block is None when no markers exist."""
    starts = [i for i, l in enumerate(lines) if l.lstrip().startswith(START)]
    ends = [i for i, l in enumerate(lines) if l.lstrip().startswith(END)]
    if not starts and not ends:
        return lines, None, []
    if len(starts) != 1 or len(ends) != 1:
        sys.exit(f"{label}: expected exactly one START and one END marker, "
                 f"found {len(starts)} START / {len(ends)} END.")
    s, e = starts[0], ends[0]
    if e < s:
        sys.exit(f"{label}: END marker (line {e + 1}) appears before START (line {s + 1}).")
    return lines[:s], lines[s:e + 1], lines[e + 1:]


def check_block(block, label):
    body = [l for l in block[1:-1] if l.strip()]
    rules = [l for l in body if not l.lstrip().startswith("<!--")]
    if len(rules) > MAX_RULES:
        sys.exit(f"{label}: {len(rules)} rules exceed the hard cap of {MAX_RULES}. "
                 "Adding at the cap requires a merge or retirement in the same diff.")
    for l in rules:
        if not RULE_RE.match(l.strip()):
            print(f"warning: rule line does not match the documented format "
                  f"(kept verbatim per spec): {l.strip()[:80]}", file=sys.stderr)
    return len(rules)


def main():
    if len(sys.argv) not in (2, 3):
        sys.exit("usage: python validate_rules_block.py <config_file> [<proposed_file>]")

    new_path = Path(sys.argv[-1])
    new_lines = read_exact_lines(new_path)
    pre_n, block_n, post_n = split_block(new_lines, new_path.name)
    if block_n is None:
        sys.exit(f"{new_path.name}: no managed rules block found.")
    n = check_block(block_n, new_path.name)

    if len(sys.argv) == 3:
        old_path = Path(sys.argv[1])
        old_lines = read_exact_lines(old_path)
        pre_o, block_o, post_o = split_block(old_lines, old_path.name)
        if block_o is None:
            # First run: the block may be inserted, but nothing else may change,
            # and the spec allows at most 3 initial rules.
            if n > 3:
                sys.exit(f"{new_path.name}: first-run block proposes {n} rules; "
                         "the spec allows at most 3 - rules must earn their place.")
            if old_lines != pre_n + post_n:
                sys.exit(f"{old_path.name} -> {new_path.name}: first-run insertion "
                         "must leave every existing line untouched.")
        elif pre_o != pre_n or post_o != post_n:
            for i, (a, b) in enumerate(zip(pre_o + post_o, pre_n + post_n)):
                if a != b:
                    sys.exit(f"{old_path.name} -> {new_path.name}: line outside the "
                             f"markers changed (\"{a[:60]}\" -> \"{b[:60]}\"). "
                             "Only content between the markers may be edited.")
            sys.exit(f"{old_path.name} -> {new_path.name}: content outside the "
                     "markers was added or removed. Only the block may change.")

    print(f"ok: {n} rule(s), markers intact"
          + ("" if len(sys.argv) == 2 else ", outside-marker content unchanged"),
          file=sys.stderr)


if __name__ == "__main__":
    main()
