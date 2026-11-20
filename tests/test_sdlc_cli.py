"""Tests for .claude/sdlc/sdlc.py, run as a subprocess in throwaway folders.

Run with: ``python3 -m unittest discover tests``
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / ".claude" / "sdlc" / "sdlc.py"
KEY = "SOC-15"
INIT = ["state", "init", KEY, "--jira-server", "mcp__Atlassian__", "--cloud-id", "cid-1"]


class CliCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(os.path.realpath(self.tmp.name))
        self.env = {**os.environ, "SDLC_NO_SAY": "1", "CLAUDE_PROJECT_DIR": str(self.root)}

    def tearDown(self):
        self.tmp.cleanup()

    def run_cli(self, *args, cwd=None, expect=0):
        proc = subprocess.run([sys.executable, "-I", str(SCRIPT), *args], cwd=cwd or self.root,
                              env=self.env, capture_output=True, text=True)
        self.assertEqual(proc.returncode, expect, f"{args}: {proc.stdout}{proc.stderr}")
        return json.loads(proc.stdout) if proc.stdout.strip() else None

    @property
    def state_path(self):
        return self.root / ".sdlc" / f"{KEY}.json"

    def state(self):
        return json.loads(self.state_path.read_text(encoding="utf-8"))

    def write_state(self, state):
        self.state_path.write_text(json.dumps(state), encoding="utf-8")


class InitTests(CliCase):
    def test_default_init_matches_the_documented_shape(self):
        out = self.run_cli(*INIT)
        self.assertEqual(out["next"], {"stage": "01", "skill": "01-investigate-task", "args": KEY})
        self.assertIsNone(out["warning"])
        s = self.state()
        self.assertEqual((s["mode"], s["from"], s["until"], s["worktree"]), ("chained", "01", "06", True))
        self.assertEqual(s["pipeline_root"], str(self.root))
        self.assertEqual(s["jira"], {"server_prefix": "mcp__Atlassian__", "cloud_id": "cid-1", "review_transition": None})
        self.assertEqual(s["stages"]["01"]["status"], "in_progress")
        self.assertEqual([s["stages"][n]["status"] for n in ("02", "03", "04", "05", "06")], ["pending"] * 5)
        self.assertEqual(s["stages"]["07"]["status"], "skipped")
        self.assertEqual((s["current_stage"], s["halted"], s["notes"], s["repos"]), ("01", None, [], []))

    def test_range_skips_outside_stages_and_until_07_warns(self):
        out = self.run_cli(*INIT, "--from", "05", "--until", "07", "--no-worktree")
        self.assertIn("MERGE", out["warning"])
        s = self.state()
        self.assertEqual([s["stages"][n]["status"] for n in ("01", "02", "03", "04")], ["skipped"] * 4)
        self.assertEqual(s["stages"]["05"]["status"], "in_progress")
        self.assertFalse(s["worktree"])

    def test_bad_arguments_are_refused_without_writing(self):
        self.assertEqual(self.run_cli(*INIT, "--from", "04", "--until", "02", expect=1)["ok"], False)
        self.run_cli("state", "init", "soc15", "--check", expect=1)
        self.run_cli(*INIT, "--until", "09", expect=2)
        self.assertFalse(self.state_path.exists())

    def test_check_validates_without_writing_or_jira_facts(self):
        out = self.run_cli("state", "init", KEY, "--until", "07", "--check")
        self.assertTrue(out["check"])
        self.assertIn("MERGE", out["warning"])
        self.assertFalse(self.state_path.exists())

    def test_jira_facts_are_required_to_create(self):
        self.run_cli("state", "init", KEY, expect=1)

    def test_existing_file_is_refused_with_the_three_options(self):
        self.run_cli(*INIT)
        out = self.run_cli(*INIT, expect=1)
        self.assertEqual(out["current_stage"], "01")
        self.assertEqual(len(out["options"]), 3)
        self.run_cli("state", "init", KEY, "--check", expect=1)


class LocateTests(CliCase):
    def test_no_file_is_standalone(self):
        out = self.run_cli("state", "locate", KEY, "--stage", "03")
        self.assertEqual(out["mode"], "standalone")
        self.assertIsNone(out["file"])

    def test_running_stage_is_chained_and_returns_pipeline_facts(self):
        self.run_cli(*INIT)
        out = self.run_cli("state", "locate", KEY, "--stage", "01")
        self.assertEqual(out["mode"], "chained")
        self.assertEqual(out["jira"]["cloud_id"], "cid-1")

    def test_stale_file_is_standalone_with_a_reason(self):
        self.run_cli(*INIT)
        out = self.run_cli("state", "locate", KEY, "--stage", "03")
        self.assertEqual(out["mode"], "standalone")
        self.assertTrue(out["stale"])
        self.assertIn("stage 03 is 'pending'", out["reason"])
        s = self.state()
        s["mode"] = "manual"
        s["stages"]["03"]["status"] = "in_progress"
        self.write_state(s)
        self.assertIn("mode is 'manual'", self.run_cli("state", "locate", KEY, "--stage", "03")["reason"])

    def test_wrong_key_in_file_is_standalone(self):
        self.run_cli(*INIT)
        s = self.state()
        s["jira_key"] = "SOC-99"
        self.write_state(s)
        self.assertIn("jira_key", self.run_cli("state", "locate", KEY, "--stage", "01")["reason"])

    def test_found_from_a_worktree_below_the_root(self):
        self.run_cli(*INIT)
        worktree = self.root / ".worktrees" / KEY
        worktree.mkdir(parents=True)
        self.assertEqual(self.run_cli("state", "locate", KEY, "--stage", "01", cwd=worktree)["mode"], "chained")

    def test_never_looks_above_the_project_root(self):
        project = self.root / "project"
        project.mkdir()
        self.run_cli(*INIT)  # a file in the parent of the project
        self.env["CLAUDE_PROJECT_DIR"] = str(project)
        self.assertEqual(self.run_cli("state", "locate", KEY, "--stage", "01", cwd=project)["mode"], "standalone")

    def test_corrupt_file_is_standalone(self):
        self.state_path.parent.mkdir()
        self.state_path.write_text("{not json", encoding="utf-8")
        out = self.run_cli("state", "locate", KEY, "--stage", "01")
        self.assertEqual(out["mode"], "standalone")
        self.assertIn("unreadable", out["reason"])


class AdvanceTests(CliCase):
    EXPECTED = {
        "01": ("02-start-task", f"{KEY} --worktree"),
        "02": ("03-dev-execute", KEY),
        "03": ("04-reconcile-work", KEY),
        "04": ("05-create-pr", KEY),
        "05": ("06-pr-review", KEY),
        "06": ("07-complete-task", KEY),
    }

    def test_each_stage_hands_off_to_the_next_skill(self):
        self.run_cli(*INIT, "--until", "07")
        for num, (skill, args) in self.EXPECTED.items():
            with self.subTest(stage=num):
                out = self.run_cli("state", "advance", KEY, num)
                self.assertEqual((out["next"]["skill"], out["next"]["args"]), (skill, args))
                s = self.state()
                self.assertEqual(s["stages"][num]["status"], "done")
                self.assertIn("finished_at", s["stages"][num])
                self.assertEqual(s["current_stage"], out["next"]["stage"])
                self.assertEqual(s["stages"][out["next"]["stage"]]["status"], "in_progress")
        out = self.run_cli("state", "advance", KEY, "07")
        self.assertTrue(out["finished"])
        self.assertIn("PR merged and SOC-15 is Done", out["message"])

    def test_no_worktree_drops_the_flag(self):
        self.run_cli(*INIT, "--no-worktree")
        self.assertEqual(self.run_cli("state", "advance", KEY, "01")["next"]["args"], KEY)

    def test_default_run_never_reaches_07(self):
        self.run_cli(*INIT, "--from", "06")
        out = self.run_cli("state", "advance", KEY, "06")
        self.assertTrue(out["finished"])
        self.assertNotIn("next", out)
        self.assertIn("Pipeline finished before merge", out["message"])
        self.assertIn("/07-complete-task SOC-15", out["message"])
        s = self.state()
        self.assertIsNone(s["current_stage"])
        self.assertIsNotNone(s["completed_at"])
        self.assertEqual(s["stages"]["07"]["status"], "skipped")

    def test_early_until_names_the_next_manual_step(self):
        self.run_cli(*INIT, "--until", "01")
        out = self.run_cli("state", "advance", KEY, "01")
        self.assertIn("/02-start-task SOC-15 --worktree", out["message"])

    def test_advancing_a_stage_that_is_not_running_is_refused(self):
        self.run_cli(*INIT)
        out = self.run_cli("state", "advance", KEY, "03", expect=1)
        self.assertIn("not 'in_progress'", out["reason"])
        self.assertEqual(self.state()["stages"]["03"]["status"], "pending")

    def test_repeating_advance_after_compaction_repeats_the_answer(self):
        self.run_cli(*INIT)
        first = self.run_cli("state", "advance", KEY, "01")
        again = self.run_cli("state", "advance", KEY, "01")
        self.assertTrue(again["already_advanced"])
        self.assertEqual(again["next"], first["next"])
        self.assertEqual(self.state()["stages"]["03"]["status"], "pending")

    def test_no_state_file_is_refused(self):
        self.run_cli("state", "advance", KEY, "01", expect=1)


class HaltResumeTests(CliCase):
    def test_halt_records_reason_and_resume_restarts_the_stage(self):
        self.run_cli(*INIT)
        self.run_cli("state", "advance", KEY, "01")
        out = self.run_cli("state", "halt", KEY, "02", "--reason", "dirty tree\nin api")
        self.assertIn("/00-run-sdlc SOC-15 --resume", out["message"])
        s = self.state()
        self.assertEqual(s["stages"]["02"]["status"], "failed")
        self.assertEqual(s["halted"]["stage"], "02")
        self.assertEqual(s["halted"]["reason"], "dirty tree in api")
        # A halted stage is no longer chained: it must not advance.
        self.run_cli("state", "advance", KEY, "02", expect=1)
        out = self.run_cli("state", "resume", KEY)
        self.assertEqual(out["next"]["skill"], "02-start-task")
        s = self.state()
        self.assertIsNone(s["halted"])
        self.assertEqual((s["current_stage"], s["stages"]["02"]["status"]), ("02", "in_progress"))

    def test_halt_carries_the_advisory_diff(self):
        self.run_cli(*INIT, "--from", "06")
        diff = self.root / "diff.json"
        diff.write_text(json.dumps({"api": {"new": [], "fixed": ["GHSA-1"], "unchanged": ["GHSA-2"]}}), encoding="utf-8")
        self.run_cli("state", "halt", KEY, "06", "--reason", "pre-existing audit failure", "--advisory-diff", str(diff))
        self.assertEqual(self.state()["halted"]["advisory_diff"]["api"]["unchanged"], ["GHSA-2"])

    def test_malformed_advisory_diff_is_refused_before_writing(self):
        self.run_cli(*INIT, "--from", "06")
        diff = self.root / "diff.json"
        diff.write_text(json.dumps({"api": {"new": []}}), encoding="utf-8")
        self.run_cli("state", "halt", KEY, "06", "--reason", "x", "--advisory-diff", str(diff), expect=1)
        self.assertIsNone(self.state()["halted"])

    def test_only_a_running_stage_can_halt(self):
        self.run_cli(*INIT)
        self.run_cli("state", "halt", KEY, "04", "--reason", "x", expect=1)

    def test_resume_of_a_finished_pipeline_reports_nothing_to_do(self):
        self.run_cli(*INIT, "--from", "06")
        self.run_cli("state", "advance", KEY, "06")
        out = self.run_cli("state", "resume", KEY)
        self.assertTrue(out["finished"])
        self.assertNotIn("next", out)


class StatusResetNoteTests(CliCase):
    def test_status_summarises_current_and_halted(self):
        self.run_cli("state", "status", KEY, expect=1)
        self.run_cli(*INIT)
        out = self.run_cli("state", "status", KEY)
        self.assertIn("stage 01", out["summary"])
        self.assertIn("| 07 | /07-complete-task | skipped |", out["table"])
        self.run_cli("state", "halt", KEY, "01", "--reason", "ticket not found")
        self.assertIn("halted at stage 01", self.run_cli("state", "status", KEY)["summary"])

    def test_note_appends_and_reset_removes(self):
        self.run_cli(*INIT)
        self.run_cli("state", "note", KEY, "Ready with conditions: update README")
        self.assertEqual(self.state()["notes"], ["Ready with conditions: update README"])
        self.assertTrue(self.run_cli("state", "reset", KEY)["removed"])
        self.assertFalse(self.state_path.exists())
        self.assertFalse(self.run_cli("state", "reset", KEY)["removed"])

    def test_writes_leave_no_temp_files(self):
        self.run_cli(*INIT)
        self.run_cli("state", "advance", KEY, "01")
        self.assertEqual(sorted(p.name for p in self.state_path.parent.iterdir()), [f"{KEY}.json"])


if __name__ == "__main__":
    unittest.main()
