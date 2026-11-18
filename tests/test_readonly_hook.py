"""Tests for .claude/hooks/approve-readonly-bash.py.

The hook may only answer "allow" for commands that are provably read-only and
stay inside the project. Everything else must fall through (return None /
print nothing) so the normal permission flow decides.

Run with: ``python3 -m unittest discover tests``
"""

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
HOOK = REPO / ".claude" / "hooks" / "approve-readonly-bash.py"


def load_hook():
    spec = importlib.util.spec_from_file_location("approve_readonly_bash", HOOK)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


hook = load_hook()


class HookFixture(unittest.TestCase):
    """A fake multi-repo project with a worktree, so path checks are realistic."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.project = os.path.realpath(cls.tmp.name)
        for sub in ("prayerLINK_api", "prayerLINK_app", ".worktrees/PW-1", ".sdlc"):
            os.makedirs(os.path.join(cls.project, sub), exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def allow(self, command, cwd=None):
        reason = hook.decide(command, self.project, cwd or self.project)
        self.assertIsNotNone(reason, f"should be allowed: {command!r}")
        self.assertTrue(reason.startswith("sdlc read-only hook: "), reason)
        return reason

    def unsure(self, command, cwd=None):
        reason = hook.decide(command, self.project, cwd or self.project)
        self.assertIsNone(reason, f"should fall through: {command!r} -> {reason}")


class ScreenshotCommandsAreAllowed(HookFixture):
    """The exact shapes that prompted in the user's sessions."""

    def test_cd_then_grep_and_version_checks(self):
        self.allow(
            "cd prayerLINK_api && grep -nE '\"@nestjs/|\"resolutions\"' package.json; echo ---; "
            "grep -nE '^\"?@nestjs/(core|platform-express|testing)@' -A3 yarn.lock | head -40; echo ---; "
            "ls .yarnrc* .nvmrc 2>/dev/null; yarn --version; node --version"
        )

    def test_cd_then_git_log_with_awkward_quoting(self):
        self.allow(
            "cd prayerLINK_api && git log --oneline -S'\"@nestjs/common\": \"^11.2.1\"' -- package.json | head -3; "
            "echo ---; git log -1 --format='%h %ad %s' --date=short -S'common-11.2.1.tgz' -- yarn.lock; "
            "echo ---; ls .github/workflows/ && grep -n 'audit' .github/workflows/*.yml | head -20"
        )

    def test_for_loop_over_repos(self):
        self.allow(
            "for r in prayerLINK_api prayerLINK_app; do echo \"== $r\"; "
            "grep -n -A2 '\"@protobufjs/utf8@' $r/yarn.lock 2>/dev/null || "
            "grep -n -A2 'protobufjs/utf8' $r/package-lock.json 2>/dev/null | head -6 || echo \"no lockfile match\"; done; "
            "echo \"== app CI audit step:\"; grep -n 'audit' prayerLINK_app/.github/workflows/*.yml"
        )

    def test_cd_then_git_show_and_status(self):
        self.allow(
            "cd prayerLINK_app && git log --format='%h %ad %s' --date=short -3 -- yarn.lock && echo \"--- diff:\" && "
            "git show e85fe07 -- yarn.lock | grep -n -A3 'protobufjs/utf8' | head -20 && "
            "git branch --show-current && git status --short | head -5"
        )

    def test_sed_print_range_and_git_show(self):
        self.allow(
            "cd prayerLINK_api && sed -n '410,432p' ../SECURITY_AUDIT.md; echo ---; "
            "git show c7784a4 --stat | head -20; echo ---; git show c7784a4 -- package.json | grep -E '^[-+].*@nestjs'"
        )


class PipelineCommandsAreAllowed(HookFixture):
    def test_git_dash_c_inside_project(self):
        self.allow("git -C prayerLINK_api status --short")
        self.allow(f"git -C {self.project}/prayerLINK_app branch --show-current")

    def test_worktree_cd_and_status(self):
        self.allow("cd .worktrees/PW-1 && git status --short")
        self.allow("git worktree list")

    def test_state_file_helpers(self):
        self.allow("date -u +%Y-%m-%dT%H:%M:%SZ")
        self.allow("jq -r .current_stage .sdlc/PW-1.json")
        self.allow("cat .sdlc/PW-1.json | jq '.stages'")

    def test_dependency_investigation(self):
        self.allow("yarn why @protobufjs/utf8 2>/dev/null; echo ---; yarn why protobufjs 2>/dev/null")
        self.allow("yarn npm audit --all --recursive --json 2>/dev/null | grep -c 'GHSA-q6x5-8v7m-xcrf'")
        self.allow("npm view @nestjs/common version")
        self.allow("yarn --cwd prayerLINK_api why x")

    def test_announcements_and_misc(self):
        self.allow("say finished investigating the task PW-272")
        self.allow("ls -d */")
        self.allow("[ -d \"prayerLINK_api/.git\" ]")
        self.allow("git log --oneline main..HEAD | wc -l")
        self.allow("find . -name '*.ts' -not -path '*/node_modules/*' | head")
        self.allow("PAGER=cat git log -3")
        self.allow("timeout 30 git log -1")
        self.allow("ls 2>&1 | head")
        self.allow("awk '{print $1\" \"$2}' file.txt")
        self.allow("sort -k2 file | uniq -c")
        self.allow("xargs grep pattern")

    def test_git_readonly_subcommand_shapes(self):
        for cmd in ("git branch -a", "git branch --list 'feature/*'", "git tag -l", "git remote -v",
                    "git stash list", "git config --get remote.origin.url", "git rev-parse --abbrev-ref HEAD",
                    "git diff main..HEAD --stat", "git blame -L 1,5 README.md"):
            with self.subTest(cmd=cmd):
                self.allow(cmd)

    def test_git_grep_npm_search_and_corepack_yarn(self):
        self.allow("git -C prayerLINK_app grep -n -e \"domexception\" -e '^\"jsdom@' origin/main -- yarn.lock package.json")
        self.allow("npm search react-navigation")
        self.allow("corepack yarn why jsdom")
        self.allow("corepack yarn --version")
        self.unsure("git grep -O vim foo")
        self.unsure("git grep --open-files-in-pager=vim foo")
        self.unsure("corepack yarn install")
        self.unsure("corepack enable")

    def test_reason_names_the_segments(self):
        reason = self.allow("cd prayerLINK_api && git log -3 | head")
        self.assertEqual(reason, "sdlc read-only hook: cd, git log, head")


class WritesAndEscapesFallThrough(HookFixture):
    def test_git_writes(self):
        for cmd in ("git push --force origin main", "git push", "git commit -m x", "git branch -D x",
                    "git branch newbranch", "git branch -m a b", "git worktree add .worktrees/x -b y",
                    "git stash", "git config user.name bob", "git remote add x y",
                    "git log --output=/tmp/x", "git -c core.pager=rm log", "git diff --ext-diff",
                    "GIT_EXTERNAL_DIFF=rm git diff", "cd prayerLINK_api && git push"):
            with self.subTest(cmd=cmd):
                self.unsure(cmd)

    def test_paths_outside_the_project(self):
        for cmd in ("cd .. && git log", "cd /etc && ls", "git -C /etc log", "cd ~ && ls", "cd && ls",
                    "cd - && ls", "git -C prayerLINK_api log && cd /tmp && ls", "yarn --cwd /tmp why x"):
            with self.subTest(cmd=cmd):
                self.unsure(cmd)

    def test_file_writes_and_exec_flags(self):
        for cmd in ("find . -delete", "find . -name '*.tmp' -exec rm {} +", "find . -name *.tmp -delete",
                    "find . -delete 2>/dev/null", "grep x > out.txt", "ls > /tmp/out", "git log 2>out.txt",
                    "sed -i 's/a/b/' f", "sed -n '/x/w out' f", "sed -n 's/a/b/p' f",
                    "awk 'BEGIN{system(\"rm x\")}'", "sort -o out in", "echo hi | tee out",
                    "say -o out.aiff hi", "date -s 10:00", "xargs -n1 rm", "rg --pre cat x",
                    "npm audit fix", "yarn audit fix", "yarn add x", "docker -H tcp://x ps",
                    "ls > /dev/null && rm x", "rm .sdlc/PW-1.json"):
            with self.subTest(cmd=cmd):
                self.unsure(cmd)

    def test_code_execution_and_shell_escapes(self):
        for cmd in ("echo $(rm -rf /)", "ls $(pwd)", "ls `pwd`", "ls; (rm x)", "cat f | sh",
                    "python3 -c 'print(1)'", "node -e 'x'", "$cmd foo", "/bin/rm x", "eval ls", "sudo ls",
                    "env -i ls", "cat <<EOF > f\nhi\nEOF", "ls\nrm -rf /", "echo foo#bar; rm x",
                    "ls # && rm -rf /", "for PATH in a b; do echo $PATH; done", "npm test &&"):
            with self.subTest(cmd=cmd):
                self.unsure(cmd)

    def test_empty_and_oversized(self):
        self.unsure("")
        self.unsure("ls " + "a" * 10_001)


class StdinContract(unittest.TestCase):
    """Drive the script the way Claude Code does: JSON on stdin, JSON or nothing on stdout."""

    def run_hook(self, payload, project_dir=None):
        env = dict(os.environ)
        env.pop("SDLC_HOOK_DEBUG", None)
        if project_dir:
            env["CLAUDE_PROJECT_DIR"] = project_dir
        return subprocess.run(
            [sys.executable, "-I", str(HOOK)],
            input=payload if isinstance(payload, str) else json.dumps(payload),
            capture_output=True, text=True, env=env, timeout=10,
        )

    def test_allow_prints_the_decision(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, "api"))
            proc = self.run_hook({"tool_name": "Bash", "cwd": tmp,
                                  "tool_input": {"command": "cd api && git log -3 --oneline"}}, tmp)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        out = json.loads(proc.stdout)
        self.assertEqual(out["hookSpecificOutput"]["hookEventName"], "PreToolUse")
        self.assertEqual(out["hookSpecificOutput"]["permissionDecision"], "allow")
        self.assertIn("git log", out["hookSpecificOutput"]["permissionDecisionReason"])

    def test_unsure_prints_nothing(self):
        proc = self.run_hook({"tool_name": "Bash", "tool_input": {"command": "git push --force origin main"}})
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(proc.stdout, "")

    def test_other_tools_and_bad_input_are_ignored(self):
        for payload in ({"tool_name": "Read", "tool_input": {}}, "not json", {"tool_name": "Bash"}):
            with self.subTest(payload=payload):
                proc = self.run_hook(payload)
                self.assertEqual(proc.returncode, 0)
                self.assertEqual(proc.stdout, "")

    def test_script_is_executable(self):
        self.assertTrue(os.access(HOOK, os.X_OK), "hook must be chmod +x")


if __name__ == "__main__":
    unittest.main()
