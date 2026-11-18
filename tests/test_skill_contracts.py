"""Structural contract tests for the SDLC skills.

The skills are markdown executed by an AI agent, so these tests check the
invariants the chaining design depends on rather than running the skills:

- every stage skill ends with the "Stop or Hand Off" section and keeps the
  standalone NO AUTO-CHAINING wording
- each stage hands off to the correct next skill, 06 guards the merge behind
  ``--until 07``, and 07 invokes nothing
- the runner documents its defaults (01 -> 06, worktree on) and its state file
  example is valid JSON with the expected shape
- every ``/NN-skill`` reference in the docs resolves to a real skill directory
- the pipeline state directory is gitignored

Run with: ``python3 -m unittest discover tests``
"""

import json
import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SKILLS = REPO / ".claude" / "skills"

STAGES = {
    "01": "01-investigate-task",
    "02": "02-start-task",
    "03": "03-dev-execute",
    "04": "04-reconcile-work",
    "05": "05-create-pr",
    "06": "06-pr-review",
    "07": "07-complete-task",
}
RUNNER = "00-run-sdlc"

HANDOFF_HEADING = "## ⛔ Stop or Hand Off"
OLD_HEADING = "## ⛔ Stop Here"

STANDALONE_BULLETS = [
    "- Do NOT invoke the next skill automatically under any circumstances",
    "- Do NOT continue even if resuming after a context compaction or conversation summary",
    '- Do NOT infer that the user wants the next step because it was "pending" in a summary',
    "- The user MUST type the next slash command explicitly to proceed",
    "- Merging, closing tickets, or any irreversible action requires explicit user invocation — never infer consent from a prior conversation",
]


def read(name: str) -> str:
    return (SKILLS / name / "skill.md").read_text(encoding="utf-8")


def handoff_section(text: str) -> str:
    idx = text.rfind(HANDOFF_HEADING)
    if idx == -1:
        raise AssertionError(f"missing {HANDOFF_HEADING!r}")
    return text[idx:]


class SkillLayoutTests(unittest.TestCase):
    def test_every_skill_has_a_skill_md(self):
        for name in [RUNNER, *STAGES.values()]:
            with self.subTest(skill=name):
                self.assertTrue((SKILLS / name / "skill.md").is_file(), name)

    def test_stage_skills_end_with_handoff_section(self):
        for num, name in STAGES.items():
            text = read(name)
            with self.subTest(stage=num):
                self.assertNotIn(OLD_HEADING, text, "old Stop Here block still present")
                self.assertEqual(text.count(HANDOFF_HEADING), 1)
                # The hand-off must be the final H2 in the file.
                last_h2 = [m.group(0) for m in re.finditer(r"^## .*$", text, re.M)][-1]
                self.assertEqual(last_h2, HANDOFF_HEADING)

    def test_runner_keeps_a_plain_stop_block(self):
        text = read(RUNNER)
        self.assertIn(OLD_HEADING, text)
        self.assertNotIn(HANDOFF_HEADING, text)


class StandaloneSafetyTests(unittest.TestCase):
    def test_standalone_wording_is_preserved_in_every_stage(self):
        for num, name in STAGES.items():
            section = handoff_section(read(name))
            with self.subTest(stage=num):
                for bullet in STANDALONE_BULLETS:
                    self.assertIn(bullet, section)

    def test_each_stage_validates_its_own_number(self):
        for num, name in STAGES.items():
            section = handoff_section(read(name))
            with self.subTest(stage=num):
                self.assertIn(f'`stages["{num}"].status` is `"in_progress"`', section)
                self.assertIn('`mode` is `"chained"`', section)
                self.assertIn("`jira_key` equals the Jira key this skill was invoked with", section)

    def test_each_stage_carries_the_compaction_rule(self):
        for num, name in STAGES.items():
            section = handoff_section(read(name))
            with self.subTest(stage=num):
                self.assertIn("**Compaction rule**", section)
                self.assertIn("re-read the file before acting", section)
                self.assertIn("Never continue because a summary says", section)

    def test_state_file_lookup_walks_ancestors(self):
        for num, name in STAGES.items():
            section = handoff_section(read(name))
            with self.subTest(stage=num):
                self.assertIn("`.sdlc/<JIRA-KEY>.json`", section)
                self.assertIn("each ancestor directory", section)


class HandoffChainTests(unittest.TestCase):
    INVOKE = re.compile(r"invoke the next stage via the Skill tool: skill `([0-9]{2}-[a-z-]+)`")

    def test_each_stage_hands_off_to_the_next_skill(self):
        order = list(STAGES.items())
        for (num, name), (next_num, next_name) in zip(order, order[1:]):
            section = handoff_section(read(name))
            with self.subTest(stage=num):
                found = self.INVOKE.findall(section)
                self.assertEqual(found, [next_name], f"stage {num} must hand off to {next_name}")
                self.assertIn(f'`stages["{next_num}"].status = "in_progress"`', section)
                self.assertIn(f'`current_stage = "{next_num}"`', section)

    def test_stage_01_passes_worktree_flag_through_to_02(self):
        section = handoff_section(read(STAGES["01"]))
        self.assertIn("append `--worktree` when the state file has `\"worktree\": true`", section)

    def test_stage_06_guards_merge_behind_until_07(self):
        section = handoff_section(read(STAGES["06"]))
        self.assertIn('**only if the state file says `"until": "07"`**', section)
        self.assertIn("Do NOT invoke `07-complete-task`", section)
        self.assertIn('Only if `until` is `"07"`', section)

    def test_stage_07_is_terminal(self):
        section = handoff_section(read(STAGES["07"]))
        self.assertEqual(self.INVOKE.findall(section), [])
        self.assertIn("This is always the final stage", section)
        self.assertNotIn('.status = "in_progress"`', section)

    def test_every_stage_halts_without_invoking_next(self):
        for num, name in STAGES.items():
            section = handoff_section(read(name))
            with self.subTest(stage=num):
                self.assertIn(f'`stages["{num}"].status = "failed"`', section)
                self.assertIn("Do NOT invoke the next stage", section)
                self.assertIn("--resume", section)


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.text = read(RUNNER)

    def test_usage_line_lists_all_flags(self):
        usage = "/00-run-sdlc <JIRA-KEY> [--from NN] [--until NN] [--no-worktree] [--resume] [--reset] [--status]"
        self.assertIn(usage, self.text)

    def test_defaults_are_01_to_06_with_worktree_on(self):
        self.assertRegex(self.text, r"\| `--from NN`\s*\| No\s*\| `01`")
        self.assertRegex(self.text, r"\| `--until NN`\s*\| No\s*\| `06`")
        self.assertIn("Worktree mode is the **default**", self.text)
        self.assertIn("unless `--no-worktree` was given", self.text)

    def test_until_07_prints_a_merge_warning(self):
        self.assertIn("--until 07 will MERGE the pull request(s)", self.text)

    def test_existing_state_file_is_refused_without_a_flag(self):
        self.assertIn("**Refuse.**", self.text)
        for flag in ("--resume", "--reset", "--status"):
            self.assertIn(flag, self.text)

    def test_state_file_example_is_valid_json_with_expected_shape(self):
        match = re.search(r"```json\n(.*?)\n```", self.text, re.S)
        self.assertIsNotNone(match, "runner must include a JSON state file example")
        state = json.loads(match.group(1))
        self.assertEqual(state["mode"], "chained")
        self.assertEqual(state["from"], "01")
        self.assertEqual(state["until"], "06")
        self.assertIs(state["worktree"], True)
        self.assertEqual(sorted(state["stages"]), sorted(STAGES))
        self.assertEqual(state["stages"]["01"]["status"], "in_progress")
        self.assertEqual(state["stages"]["07"]["status"], "skipped")
        for num in ("02", "03", "04", "05", "06"):
            self.assertEqual(state["stages"][num]["status"], "pending")
        self.assertIsNone(state["halted"])
        self.assertEqual(state["notes"], [])

    def test_announcements_are_defined_for_stages_to_reference(self):
        self.assertIn("**Finished**", self.text)
        self.assertIn("**Halted**", self.text)
        self.assertIn("say finished the SDLC pipeline for {SOC-XX}", self.text)
        self.assertIn("say the SDLC pipeline halted at stage {NN} for {SOC-XX}", self.text)

    def test_runner_invokes_every_stage_by_name(self):
        for name in STAGES.values():
            self.assertIn(f"skill `{name}`", self.text)


class CrossReferenceTests(unittest.TestCase):
    REF = re.compile(r"/(\d{2}-[a-z][a-z-]+)")

    def test_every_numbered_skill_reference_resolves(self):
        docs = list(SKILLS.glob("*/skill.md")) + [SKILLS / "README.md"]
        known = {RUNNER, *STAGES.values()}
        for doc in docs:
            refs = set(self.REF.findall(doc.read_text(encoding="utf-8")))
            with self.subTest(doc=doc.relative_to(REPO)):
                self.assertTrue(refs <= known, f"unknown skill references: {sorted(refs - known)}")

    def test_readme_documents_the_runner(self):
        readme = (SKILLS / "README.md").read_text(encoding="utf-8")
        self.assertIn("/00-run-sdlc", readme)
        self.assertIn("--no-worktree", readme)
        self.assertIn("python3 -m unittest discover tests", readme)


class ConventionsTests(unittest.TestCase):
    HEADING = "## Shell & Tool Conventions"

    def test_every_skill_carries_the_conventions_block_before_usage(self):
        for name in [RUNNER, *STAGES.values()]:
            text = read(name)
            with self.subTest(skill=name):
                self.assertEqual(text.count(self.HEADING), 1)
                self.assertLess(text.index(self.HEADING), text.index("## Usage"))
                self.assertIn("Never `cd <dir> && git …`", text)
                self.assertIn("`jq` only", text)

    def test_state_file_lookup_never_leaves_the_project(self):
        for num, name in STAGES.items():
            section = handoff_section(read(name))
            with self.subTest(stage=num):
                self.assertIn("never above it", section)
                self.assertIn("`Edit` tool", section)

    def test_runner_writes_state_without_shell_redirects(self):
        text = read(RUNNER)
        self.assertIn("with the `Write` tool", text)
        self.assertIn("rm .sdlc/<JIRA-KEY>.json", text)
        self.assertIn("git -C <absolute-repo-path> status --short", text)


class PermissionTemplateTests(unittest.TestCase):
    TEMPLATE = REPO / "templates" / "project-settings.json"
    HOOK_SCRIPT = "approve-readonly-bash.py"
    BASH_RULE = re.compile(r"^Bash\((.*)\)$")

    def load(self, path):
        return json.loads(path.read_text(encoding="utf-8"))

    def hook_commands(self, settings):
        return [
            h["command"]
            for group in settings.get("hooks", {}).get("PreToolUse", [])
            if group.get("matcher") == "Bash"
            for h in group["hooks"]
        ]

    def test_template_has_allow_ask_and_hook(self):
        settings = self.load(self.TEMPLATE)
        self.assertTrue(settings["permissions"]["allow"])
        self.assertTrue(settings["permissions"]["ask"])
        self.assertTrue(any(self.HOOK_SCRIPT in c for c in self.hook_commands(settings)))
        self.assertTrue((REPO / ".claude" / "hooks" / self.HOOK_SCRIPT).is_file())

    def test_bash_rules_put_the_wildcard_after_the_subcommand(self):
        settings = self.load(self.TEMPLATE)
        for rule in settings["permissions"]["allow"] + settings["permissions"]["ask"]:
            m = self.BASH_RULE.match(rule)
            if not m:
                continue
            words = m.group(1).split(" ")
            with self.subTest(rule=rule):
                self.assertNotIn("*", words[0], "wildcard before the program name")
                self.assertNotIn(":*", rule, "use the trailing ' *' form")

    def test_destructive_shapes_are_ask_rules(self):
        ask = self.load(self.TEMPLATE)["permissions"]["ask"]
        for rule in ("Bash(git push --force*)", "Bash(git reset --hard *)", "Bash(git branch -D *)", "Bash(rm -rf *)"):
            self.assertIn(rule, ask)

    def test_repo_settings_register_the_same_hook(self):
        settings = self.load(REPO / ".claude" / "settings.json")
        self.assertTrue(any(self.HOOK_SCRIPT in c for c in self.hook_commands(settings)))

    def test_readme_documents_install_and_permissions(self):
        readme = (SKILLS / "README.md").read_text(encoding="utf-8")
        for needle in ("## Install into a project", "/hooks", "## Shell & Tool Conventions", "templates/project-settings.json", "SDLC_HOOK_DEBUG",
                       "python3 /path/to/sdlc-markdown/install.py", "--dry-run", "--preset", "--force", "--no-accept-edits"):
            self.assertIn(needle, readme)
        root = (REPO / "README.md").read_text(encoding="utf-8")
        self.assertIn("python3 install.py", root)

    def test_presets_are_valid_and_named_in_install_help(self):
        presets = sorted((REPO / "templates" / "presets").glob("*.json"))
        self.assertTrue(presets)
        for path in presets:
            with self.subTest(preset=path.name):
                data = json.loads(path.read_text(encoding="utf-8"))
                self.assertTrue(data.get("allow"))
                for rule in data["allow"]:
                    m = self.BASH_RULE.match(rule)
                    if m:
                        self.assertNotIn(":*", rule)
                        self.assertNotIn("*", m.group(1).split(" ")[0])


class GitignoreTests(unittest.TestCase):
    def test_pipeline_state_and_worktrees_are_ignored(self):
        lines = (REPO / ".gitignore").read_text(encoding="utf-8").splitlines()
        self.assertIn(".sdlc/", lines)
        self.assertIn(".worktrees/", lines)
        self.assertIn("__pycache__/", lines)


if __name__ == "__main__":
    unittest.main()
