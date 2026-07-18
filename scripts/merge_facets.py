"""Merge Claude Code /insights artifacts into one JSONL for ad-hoc analysis.

Joins session-meta/*.json (mechanical per-session stats, the superset)
with facets/*.json (LLM-written session assessments) by session_id.
Sessions without a facet get has_facet=false.

Data root: $CLAUDE_CONFIG_DIR/usage-data if CLAUDE_CONFIG_DIR is set,
otherwise ~/.claude/usage-data. These artifacts are produced by running
/insights inside Claude Code; if they are absent, this script says so
and exits non-zero instead of writing an empty dataset.

Usage:
    python merge_facets.py <output_path>

Writes one JSON object per line (UTF-8).
Coverage stats go to stderr so they never pollute the data stream.
"""
import json
import os
import sys
from pathlib import Path

# `or` (not a get-default) so an empty env var also falls back - matching
# extract_claude_raw.py; a get-default would resolve "" to the current dir.
CONFIG_DIR = Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")
BASE = CONFIG_DIR / "usage-data"


def load_dir(d):
    for f in sorted(d.glob("*.json")):
        try:
            obj = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            print(f"skip {f.name}: {e}", file=sys.stderr)
            continue
        if not isinstance(obj, dict):
            print(f"skip {f.name}: not a JSON object", file=sys.stderr)
            continue
        yield f, obj


def build_rows():
    facets = {}
    for f, d in load_dir(BASE / "facets"):
        facets[d.get("session_id", f.stem)] = d

    rows = []
    for f, d in load_dir(BASE / "session-meta"):
        sid = d.get("session_id", f.stem)
        fac = facets.pop(sid, None)
        d["has_facet"] = fac is not None
        if fac:
            d.update({k: v for k, v in fac.items() if k != "session_id"})
        rows.append(d)

    # Facets whose meta file is missing: rare, but surface rather than drop.
    for sid, fac in facets.items():
        fac["has_facet"] = True
        fac["meta_missing"] = True
        rows.append(fac)

    rows.sort(key=lambda r: r.get("start_time", ""))
    return rows


def main():
    if len(sys.argv) < 2:
        sys.exit("usage: python merge_facets.py <output_path>")

    if not (BASE / "session-meta").is_dir():
        sys.exit(
            f"No /insights data found under {BASE}.\n"
            "Run the /insights command inside Claude Code first - it generates "
            "the session-meta and facets files this skill analyzes."
        )

    rows = build_rows()
    if not rows:
        sys.exit(f"{BASE} exists but contains no session data. Run /insights in Claude Code first.")

    with open(sys.argv[1], "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    n_fac = sum(1 for r in rows if r.get("has_facet"))
    print(
        f"sessions: {len(rows)}  with_facet: {n_fac}  meta_only: {len(rows) - n_fac}",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
