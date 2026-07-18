"""Smoke tests for the three bundled extractors, on synthetic logs.

Stdlib-only (unittest) to match the scripts' zero-dependency rule;
runs under both `python -m unittest discover tests` and `pytest tests`.
Each test builds a tiny fake log tree in a temp dir and runs the real
script as a subprocess, the same way the skill invokes it.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"


def run_script(script, args, env_extra):
    env = dict(os.environ, PYTHONUTF8="1", **env_extra)
    return subprocess.run(
        [sys.executable, str(SCRIPTS / script), *args],
        capture_output=True, text=True, encoding="utf-8", env=env,
    )


def write_jsonl(path, lines):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        for line in lines:
            fh.write(line if isinstance(line, str) else json.dumps(line, ensure_ascii=False))
            fh.write("\n")


class TestClaudeRaw(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.out = self.root / "out.jsonl"

    def tearDown(self):
        self.tmp.cleanup()

    def run_extractor(self):
        return run_script(
            "extract_claude_raw.py", [str(self.out), "7"],
            {"CLAUDE_CONFIG_DIR": str(self.root)},
        )

    def test_full_session_row(self):
        write_jsonl(self.root / "projects" / "proj" / "sess1.jsonl", [
            "this line is not json",
            {"type": "user", "origin": {"kind": "human"},
             "message": {"role": "user", "content": "幫我修 bug"},
             "timestamp": "2026-07-17T01:00:00.000Z",
             "cwd": "C:\\proj", "version": "2.1.0", "gitBranch": "main"},
            {"type": "user",
             "message": {"content": "<command-message>loop</command-message>\n<command-name>/loop</command-name>"},
             "timestamp": "2026-07-17T01:01:00.000Z"},
            {"type": "user", "message": {"content": [{"type": "tool_result", "content": "ok"}]},
             "timestamp": "2026-07-17T01:02:00.000Z"},
            {"type": "assistant", "timestamp": "2026-07-17T01:10:00.000Z",
             "message": {"id": "m1", "model": "claude-opus-4-8",
                         "usage": {"output_tokens": 100},
                         "content": [{"type": "tool_use", "name": "Skill", "input": {"skill": "writing"}}]}},
            # Same API message id again: tokens must NOT double-count.
            {"type": "assistant", "timestamp": "2026-07-17T01:10:01.000Z",
             "message": {"id": "m1", "model": "claude-opus-4-8",
                         "usage": {"output_tokens": 100},
                         "content": [{"type": "tool_use", "name": "Agent", "input": {"subagent_type": "Explore"}}]}},
            # Sidechain (subagent) traffic: excluded from every count.
            {"type": "assistant", "isSidechain": True, "timestamp": "2026-07-17T01:15:00.000Z",
             "message": {"id": "m2", "usage": {"output_tokens": 999},
                         "content": [{"type": "tool_use", "name": "Bash", "input": {}}]}},
            {"type": "assistant", "timestamp": "2026-07-17T01:30:00.000Z",
             "message": {"id": "m3", "model": "claude-opus-4-8",
                         "usage": {"output_tokens": 50}, "content": []}},
        ])
        # Newer format: subagent transcripts live in a sibling directory,
        # not as inline sidechain lines.
        write_jsonl(self.root / "projects" / "proj" / "sess1" / "subagents" / "agent-x.jsonl", [
            {"type": "assistant", "isSidechain": True,
             "message": {"id": "m9", "usage": {"output_tokens": 999}, "content": []}},
        ])
        res = self.run_extractor()
        self.assertEqual(res.returncode, 0, res.stderr)
        rows = [json.loads(l) for l in self.out.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(len(rows), 1)
        r = rows[0]
        self.assertEqual(r["human_messages"], 1)
        self.assertEqual(r["command_counts"], {"/loop": 1})
        self.assertEqual(r["skill_counts"], {"writing": 1})
        self.assertEqual(r["agent_types"], {"Explore": 1})
        self.assertEqual(r["output_tokens"], 150)  # m1 deduped, sidechain m2 excluded
        # Subagent cost visible separately: inline sidechain (old format, 999)
        # + subagents/ directory files (new format, 999).
        self.assertEqual(r["sidechain_output_tokens"], 1998)
        self.assertEqual(r["models"], ["claude-opus-4-8"])
        self.assertNotIn("Bash", r["tool_counts"])  # sidechain excluded
        self.assertEqual(r["tool_counts"]["__unparsed_lines__"], 1)
        self.assertEqual(r["duration_minutes"], 30.0)
        self.assertEqual(r["user_inputs_sample"], ["幫我修 bug"])

    def test_all_sessions_skipped_hints_schema_change(self):
        # Files exist, but nothing in them is recognizable human activity -
        # the signature of a log-format change. Must fail loudly, not write
        # an empty dataset that downstream reads as "no sessions this week".
        write_jsonl(self.root / "projects" / "proj" / "sess2.jsonl", [
            {"type": "user", "message": {"content": [{"type": "tool_result", "content": "x"}]},
             "timestamp": "2026-07-17T01:00:00.000Z"},
            {"type": "system", "timestamp": "2026-07-17T01:01:00.000Z"},
        ])
        res = self.run_extractor()
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("format", res.stderr.lower())


class TestCodex(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.out = self.root / "out.jsonl"
        self.home_env = {"HOME": str(self.root), "USERPROFILE": str(self.root)}

    def tearDown(self):
        self.tmp.cleanup()

    def test_meta_inputs_and_tokens(self):
        write_jsonl(self.root / ".codex" / "sessions" / "2026" / "07" / "17" / "rollout-1-a.jsonl", [
            {"type": "session_meta",
             "payload": {"session_id": "abc", "timestamp": "2026-07-17T01:00:00Z",
                         "cwd": "/home/u/proj", "originator": "codex_cli", "cli_version": "1.0"}},
            {"type": "event_msg", "payload": {"type": "input_text", "text": "fix the tests"}},
            {"type": "event_msg", "payload": {"type": "token_count",
                                              "info": {"total_tokens": 1234}}},
        ])
        res = run_script("extract_codex.py", [str(self.out), "7"], self.home_env)
        self.assertEqual(res.returncode, 0, res.stderr)
        rows = [json.loads(l) for l in self.out.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(len(rows), 1)
        r = rows[0]
        self.assertEqual(r["session_id"], "abc")
        self.assertEqual(r["user_inputs_sample"], ["fix the tests"])
        self.assertEqual(r["user_input_total"], 1)
        self.assertEqual(r["last_token_count"], {"total_tokens": 1234})

    def test_no_session_meta_anywhere_warns(self):
        # Every file lacking session_meta = likely format change; the rows
        # are still emitted (event counts remain usable) but stderr must say so.
        write_jsonl(self.root / ".codex" / "sessions" / "2026" / "07" / "17" / "rollout-1-b.jsonl", [
            {"type": "event_msg", "payload": {"type": "something_else"}},
        ])
        res = run_script("extract_codex.py", [str(self.out), "7"], self.home_env)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("session_meta", res.stderr)


class TestMergeFacets(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.out = self.root / "out.jsonl"

    def tearDown(self):
        self.tmp.cleanup()

    def run_merge(self):
        return run_script("merge_facets.py", [str(self.out)],
                          {"CLAUDE_CONFIG_DIR": str(self.root)})

    def test_join_by_session_id(self):
        base = self.root / "usage-data"
        (base / "session-meta").mkdir(parents=True)
        (base / "facets").mkdir(parents=True)
        (base / "session-meta" / "s1.json").write_text(
            json.dumps({"session_id": "s1", "start_time": "2026-07-15T00:00:00Z"}), encoding="utf-8")
        (base / "session-meta" / "s2.json").write_text(
            json.dumps({"session_id": "s2", "start_time": "2026-07-16T00:00:00Z"}), encoding="utf-8")
        (base / "facets" / "s1.json").write_text(
            json.dumps({"session_id": "s1", "outcome": "fully_achieved"}), encoding="utf-8")
        res = self.run_merge()
        self.assertEqual(res.returncode, 0, res.stderr)
        rows = {r["session_id"]: r for l in self.out.read_text(encoding="utf-8").splitlines()
                for r in [json.loads(l)]}
        self.assertTrue(rows["s1"]["has_facet"])
        self.assertEqual(rows["s1"]["outcome"], "fully_achieved")
        self.assertFalse(rows["s2"]["has_facet"])

    def test_missing_data_exits_nonzero(self):
        res = self.run_merge()
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("/insights", res.stderr)


class TestValidateRulesBlock(unittest.TestCase):
    BLOCK = [
        "<!-- session-analytics:rules START (weekly-reviewed; max 10; edits outside markers are never touched) -->",
        "- R1 [since 2026-07-18 | confirmed 2026-07-18] Do the thing. (evidence: 2 sessions 7/11+7/15)",
        "<!-- session-analytics:rules END -->",
    ]

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, name, lines):
        p = self.root / name
        p.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return p

    def validate(self, *paths):
        return run_script("validate_rules_block.py", [str(p) for p in paths], {})

    def test_valid_block_passes(self):
        p = self.write("c.md", ["# config", *self.BLOCK, "tail"])
        self.assertEqual(self.validate(p).returncode, 0)

    def test_over_cap_fails(self):
        rules = [f"- R{i} [since 2026-07-18 | confirmed 2026-07-18] Rule {i}. (evidence: x)"
                 for i in range(11)]
        p = self.write("c.md", [self.BLOCK[0], *rules, self.BLOCK[2]])
        res = self.validate(p)
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("cap", res.stderr)

    def test_outside_marker_edit_fails(self):
        old = self.write("old.md", ["# config", *self.BLOCK, "tail"])
        new = self.write("new.md", ["# config EDITED", *self.BLOCK, "tail"])
        res = self.validate(old, new)
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("outside", res.stderr)

    def test_block_only_edit_passes(self):
        old = self.write("old.md", ["# config", *self.BLOCK, "tail"])
        new_block = [self.BLOCK[0],
                     "- R2 [since 2026-07-18 | confirmed 2026-07-18] New rule. (evidence: y)",
                     self.BLOCK[2]]
        new = self.write("new.md", ["# config", *new_block, "tail"])
        self.assertEqual(self.validate(old, new).returncode, 0)

    def test_first_run_insertion_passes(self):
        old = self.write("old.md", ["# config", "tail"])
        new = self.write("new.md", ["# config", *self.BLOCK, "tail"])
        self.assertEqual(self.validate(old, new).returncode, 0)

    def test_missing_markers_fails(self):
        p = self.write("c.md", ["# config", "no block here"])
        self.assertNotEqual(self.validate(p).returncode, 0)

    def test_nonconforming_rule_warns_but_passes(self):
        p = self.write("c.md", [self.BLOCK[0], "- hand-added free-form rule", self.BLOCK[2]])
        res = self.validate(p)
        self.assertEqual(res.returncode, 0)
        self.assertIn("warning", res.stderr)


if __name__ == "__main__":
    unittest.main()
