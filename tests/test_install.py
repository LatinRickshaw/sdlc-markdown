"""Tests for install.py, run against throwaway project folders.

Run with: ``python3 -m unittest discover tests``
"""

import contextlib
import importlib.util
import io
import json
import os
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def load_installer():
    spec = importlib.util.spec_from_file_location("sdlc_install", REPO / "install.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


install = load_installer()
TEMPLATE = json.loads((REPO / "templates" / "project-settings.json").read_text(encoding="utf-8"))
NODE = json.loads((REPO / "templates" / "presets" / "node.json").read_text(encoding="utf-8"))


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.target = Path(os.path.realpath(self.tmp.name))
        # A multi-repo folder like prayerLINK: two sub-repos, one gitignore without a final newline.
        for repo in ("api", "app"):
            (self.target / repo / ".git").mkdir(parents=True)
            (self.target / repo / ".git" / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
        # prayerLINK's root has a stray .git folder with no HEAD; git ignores it and so must we.
        (self.target / ".git" / "info").mkdir(parents=True)
        (self.target / "app" / ".gitignore").write_text("node_modules/\n!.yarn/versions", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def run_install(self, *args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = install.main([str(self.target), *args])
        return code, out.getvalue()

    def settings(self):
        return json.loads((self.target / ".claude" / "settings.json").read_text(encoding="utf-8"))

    def hook_commands(self, settings):
        return [h["command"] for g in settings["hooks"]["PreToolUse"] for h in g["hooks"]]

    # -- fresh install --------------------------------------------------------

    def test_fresh_install_links_skills_and_hook(self):
        code, _ = self.run_install()
        self.assertEqual(code, 0)
        skills = sorted(p.name for p in (REPO / ".claude" / "skills").glob("0*"))
        self.assertTrue(skills)
        for name in skills:
            link = self.target / ".claude" / "skills" / name
            self.assertTrue(link.is_symlink(), name)
            self.assertEqual(link.resolve(), (REPO / ".claude" / "skills" / name).resolve())
        hooks = self.target / ".claude" / "hooks"
        self.assertTrue(hooks.is_symlink())
        self.assertTrue((hooks / "approve-readonly-bash.py").is_file())

    def test_fresh_install_writes_template_settings(self):
        self.run_install()
        s = self.settings()
        for name in ("allow", "ask"):
            for rule in TEMPLATE["permissions"][name]:
                self.assertIn(rule, s["permissions"][name])
        self.assertEqual(s["permissions"]["defaultMode"], "acceptEdits")
        self.assertEqual(len(self.hook_commands(s)), 1)
        self.assertNotIn("$comment", s)

    def test_gitignores_are_updated_in_every_sub_repo(self):
        self.run_install()
        api = (self.target / "api" / ".gitignore").read_text(encoding="utf-8").splitlines()
        app = (self.target / "app" / ".gitignore").read_text(encoding="utf-8").splitlines()
        self.assertEqual(api, [".sdlc/", ".worktrees/"])
        # The missing final newline must not glue ".sdlc/" onto the last line.
        self.assertEqual(app, ["node_modules/", "!.yarn/versions", ".sdlc/", ".worktrees/"])
        self.assertFalse((self.target / ".gitignore").exists(), "stray .git without HEAD is not a repo")

    def test_worktree_style_git_file_counts_as_a_repo(self):
        (self.target / "wt").mkdir()
        (self.target / "wt" / ".git").write_text("gitdir: /somewhere/.git/worktrees/wt\n", encoding="utf-8")
        self.run_install()
        self.assertTrue((self.target / "wt" / ".gitignore").is_file())

    # -- merging into an existing project ------------------------------------

    def test_existing_rules_mode_and_keys_are_preserved(self):
        path = self.target / ".claude" / "settings.json"
        path.parent.mkdir(parents=True)
        existing = {
            "permissions": {"allow": ["Bash(make test)", "Bash(git log *)"], "defaultMode": "default",
                            "additionalDirectories": ["/data"]},
            "env": {"FOO": "1"},
        }
        path.write_text(json.dumps(existing), encoding="utf-8")
        self.run_install()
        s = self.settings()
        self.assertEqual(s["permissions"]["allow"][:2], ["Bash(make test)", "Bash(git log *)"])
        self.assertEqual(s["permissions"]["allow"].count("Bash(git log *)"), 1)
        self.assertEqual(s["permissions"]["defaultMode"], "default")
        self.assertEqual(s["permissions"]["additionalDirectories"], ["/data"])
        self.assertEqual(s["env"], {"FOO": "1"})
        backups = list(path.parent.glob("settings.json.bak-*"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(json.loads(backups[0].read_text(encoding="utf-8")), existing)

    def test_ask_rules_are_removed_from_allow(self):
        path = self.target / ".claude" / "settings.json"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps({"permissions": {"allow": ["Bash(rm -rf *)"]}}), encoding="utf-8")
        self.run_install()
        perms = self.settings()["permissions"]
        self.assertNotIn("Bash(rm -rf *)", perms["allow"])
        self.assertIn("Bash(rm -rf *)", perms["ask"])

    def test_rerun_is_idempotent(self):
        self.run_install("--preset", "node")
        first = self.settings()
        code, out = self.run_install("--preset", "node")
        self.assertEqual(code, 0)
        self.assertEqual(self.settings(), first)
        self.assertIn("already has every template rule", out)
        self.assertEqual(list((self.target / ".claude").glob("settings.json.bak-*")), [])
        self.assertEqual((self.target / "api" / ".gitignore").read_text(encoding="utf-8"), ".sdlc/\n.worktrees/\n")

    def test_preset_adds_tooling_rules(self):
        self.run_install("--preset", "node")
        allow = self.settings()["permissions"]["allow"]
        for rule in NODE["allow"]:
            self.assertIn(rule, allow)

    def test_allows_reading_the_sdlc_checkout(self):
        self.run_install()
        self.assertIn(f"Read(/{REPO.resolve()}/**)", self.settings()["permissions"]["allow"])

    def test_no_accept_edits_leaves_mode_unset(self):
        self.run_install("--no-accept-edits")
        self.assertNotIn("defaultMode", self.settings()["permissions"])

    # -- safety ---------------------------------------------------------------

    def test_dry_run_writes_nothing(self):
        code, out = self.run_install("--dry-run")
        self.assertEqual(code, 0)
        self.assertIn("[dry-run]", out)
        self.assertFalse((self.target / ".claude").exists())
        self.assertFalse((self.target / "api" / ".gitignore").exists())

    def test_real_directories_are_never_replaced(self):
        skill = self.target / ".claude" / "skills" / "01-investigate-task"
        skill.mkdir(parents=True)
        (skill / "skill.md").write_text("local copy", encoding="utf-8")
        code, out = self.run_install()
        self.assertEqual(code, 1)
        self.assertIn("CONFLICT", out)
        self.assertEqual((skill / "skill.md").read_text(encoding="utf-8"), "local copy")

    def test_foreign_symlink_needs_force(self):
        other = self.target / "elsewhere"
        other.mkdir()
        link = self.target / ".claude" / "skills" / "02-start-task"
        link.parent.mkdir(parents=True)
        link.symlink_to(other)
        code, _ = self.run_install()
        self.assertEqual(code, 1)
        self.assertEqual(link.resolve(), other)
        code, _ = self.run_install("--force")
        self.assertEqual(code, 0)
        self.assertEqual(link.resolve(), (REPO / ".claude" / "skills" / "02-start-task").resolve())

    def test_existing_hooks_directory_gets_only_the_script(self):
        hooks = self.target / ".claude" / "hooks"
        hooks.mkdir(parents=True)
        (hooks / "mine.sh").write_text("#!/bin/sh\n", encoding="utf-8")
        self.run_install()
        self.assertFalse(hooks.is_symlink())
        self.assertTrue((hooks / "mine.sh").is_file())
        self.assertTrue((hooks / "approve-readonly-bash.py").is_symlink())

    def test_invalid_settings_json_is_reported_not_overwritten(self):
        path = self.target / ".claude" / "settings.json"
        path.parent.mkdir(parents=True)
        path.write_text("{ not json", encoding="utf-8")
        code, out = self.run_install()
        self.assertEqual(code, 1)
        self.assertIn("not valid JSON", out)
        self.assertEqual(path.read_text(encoding="utf-8"), "{ not json")

    def test_refuses_bad_targets(self):
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(install.main([str(self.target / "missing")]), 2)
            self.assertEqual(install.main([str(REPO)]), 2)


if __name__ == "__main__":
    unittest.main()
