"""Tests for the PreToolUse guard, driven the way the harness drives it:
JSON payload on stdin, decision JSON (or silence) on stdout, always exit 0.

Covers every branch of the plain-language contract: non-config files and
block-untouched edits pass silently; block edits that break the validator
contract are denied; whole-block removal downgrades to "ask"; garbage
input fails open.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

GUARD = Path(__file__).resolve().parent.parent / "scripts" / "guard_rules_block.py"

BLOCK = [
    "<!-- session-analytics:rules START (weekly-reviewed; max 10; edits outside markers are never touched) -->",
    "- R1 [since 2026-07-18 | confirmed 2026-07-18] Do the thing. (evidence: 2 sessions 7/11+7/15)",
    "<!-- session-analytics:rules END -->",
]


def run_guard(tool_name, tool_input):
    payload = json.dumps({"tool_name": tool_name, "tool_input": tool_input})
    return subprocess.run(
        [sys.executable, str(GUARD)],
        input=payload, capture_output=True, text=True, encoding="utf-8",
        env=dict(os.environ, PYTHONUTF8="1"),
    )


def parse_decision(res):
    """The guard's stdout: either empty (pass-through) or one decision JSON."""
    if not res.stdout.strip():
        return None
    return json.loads(res.stdout)["hookSpecificOutput"]


class TestGuard(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def config(self, lines, name="CLAUDE.md", endings="\n"):
        p = self.root / name
        p.write_bytes((endings.join(lines) + endings).encode("utf-8"))
        return p

    def test_non_config_file_passes_silently(self):
        p = self.config(["# whatever", *BLOCK], name="notes.md")
        res = run_guard("Edit", {"file_path": str(p), "old_string": "R1", "new_string": "R9"})
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIsNone(parse_decision(res))

    def test_config_without_block_passes(self):
        p = self.config(["# my rules", "be nice"])
        res = run_guard("Edit", {"file_path": str(p), "old_string": "be nice", "new_string": "be kind"})
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIsNone(parse_decision(res))

    def test_edit_outside_block_passes(self):
        # The key non-interference case: the user editing their own config.
        p = self.config(["# my rules", *BLOCK, "tail note"])
        res = run_guard("Edit", {"file_path": str(p), "old_string": "tail note", "new_string": "tail note v2"})
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIsNone(parse_decision(res))

    def test_valid_block_edit_passes(self):
        p = self.config(["# my rules", *BLOCK, "tail"])
        res = run_guard("Edit", {
            "file_path": str(p),
            "old_string": BLOCK[1],
            "new_string": "- R2 [since 2026-07-19 | confirmed 2026-07-19] New rule. (evidence: y)",
        })
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIsNone(parse_decision(res))

    def test_over_cap_write_denied(self):
        p = self.config(["# my rules", *BLOCK, "tail"])
        rules = [f"- R{i} [since 2026-07-19 | confirmed 2026-07-19] Rule {i}. (evidence: x)"
                 for i in range(11)]
        content = "\n".join(["# my rules", BLOCK[0], *rules, BLOCK[2], "tail"]) + "\n"
        res = run_guard("Write", {"file_path": str(p), "content": content})
        d = parse_decision(res)
        self.assertEqual(d["permissionDecision"], "deny", res.stdout)
        self.assertIn("cap", d["permissionDecisionReason"])

    def test_marker_damage_denied(self):
        p = self.config(["# my rules", *BLOCK, "tail"])
        res = run_guard("Edit", {"file_path": str(p), "old_string": BLOCK[2] + "\n", "new_string": ""})
        d = parse_decision(res)
        self.assertEqual(d["permissionDecision"], "deny", res.stdout)

    def test_block_plus_outside_in_one_call_denied(self):
        p = self.config(["# my rules", *BLOCK, "tail"])
        content = "\n".join(["# my rules EDITED", BLOCK[0],
                             "- R2 [since 2026-07-19 | confirmed 2026-07-19] New. (evidence: y)",
                             BLOCK[2], "tail"]) + "\n"
        res = run_guard("Write", {"file_path": str(p), "content": content})
        d = parse_decision(res)
        self.assertEqual(d["permissionDecision"], "deny", res.stdout)
        self.assertIn("拆成另一次", d["permissionDecisionReason"])

    def test_whole_block_removal_asks(self):
        p = self.config(["# my rules", *BLOCK, "tail"])
        res = run_guard("Write", {"file_path": str(p), "content": "# my rules\ntail\n"})
        d = parse_decision(res)
        self.assertEqual(d["permissionDecision"], "ask", res.stdout)
        self.assertIn("移除", d["permissionDecisionReason"])

    def test_first_run_insertion_within_cap_passes(self):
        p = self.config(["# my rules", "tail"])
        res = run_guard("Edit", {
            "file_path": str(p),
            "old_string": "# my rules\n",
            "new_string": "# my rules\n" + "\n".join(BLOCK) + "\n",
        })
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIsNone(parse_decision(res))

    def test_first_run_over_three_rules_denied(self):
        p = self.config(["# my rules", "tail"])
        rules = [f"- R{i} [since 2026-07-19 | confirmed 2026-07-19] Rule {i}. (evidence: x)"
                 for i in range(4)]
        block = "\n".join([BLOCK[0], *rules, BLOCK[2]])
        res = run_guard("Edit", {
            "file_path": str(p),
            "old_string": "# my rules\n",
            "new_string": "# my rules\n" + block + "\n",
        })
        d = parse_decision(res)
        self.assertEqual(d["permissionDecision"], "deny", res.stdout)

    def test_crlf_config_block_edit_still_guarded(self):
        # Edit payloads use \n; the file on disk may be CRLF. The guard must
        # still reconstruct the edit instead of failing open.
        p = self.config(["# my rules", BLOCK[0],
                         *[f"- R{i} [since 2026-07-19 | confirmed 2026-07-19] Rule {i}. (evidence: x)"
                           for i in range(10)],
                         BLOCK[2], "tail"], endings="\r\n")
        res = run_guard("Edit", {
            "file_path": str(p),
            "old_string": "- R9 [since 2026-07-19 | confirmed 2026-07-19] Rule 9. (evidence: x)",
            "new_string": "- R9 [since 2026-07-19 | confirmed 2026-07-19] Rule 9. (evidence: x)\n"
                          "- R10 [since 2026-07-19 | confirmed 2026-07-19] Rule 10. (evidence: x)",
        })
        d = parse_decision(res)
        self.assertEqual(d["permissionDecision"], "deny", res.stdout)
        self.assertIn("cap", d["permissionDecisionReason"])

    def test_edit_old_string_not_found_passes(self):
        # The Edit tool itself will error; the guard has nothing to judge.
        p = self.config(["# my rules", *BLOCK])
        res = run_guard("Edit", {"file_path": str(p), "old_string": "absent text", "new_string": "x"})
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIsNone(parse_decision(res))

    def test_garbage_stdin_fails_open(self):
        res = subprocess.run([sys.executable, str(GUARD)], input="not json",
                             capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertFalse(res.stdout.strip())

    def test_other_tools_pass(self):
        res = run_guard("Bash", {"command": "echo hi"})
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIsNone(parse_decision(res))


if __name__ == "__main__":
    unittest.main()
