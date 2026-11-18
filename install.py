#!/usr/bin/env python3
"""Install the SDLC skills, permission hook and permission rules into a project.

Usage:
    python3 install.py <target-project> [--preset node] [--dry-run] [--force] [--no-accept-edits]

What it does (every step is idempotent, so re-run it after changing the
template to push new rules out):

1. Symlinks each ``.claude/skills/0*`` skill into ``<target>/.claude/skills/``.
2. Symlinks ``.claude/hooks`` into ``<target>/.claude/hooks``.  If the target
   already has a real hooks directory, only the hook script is linked into it.
3. Merges ``templates/project-settings.json`` (plus any ``--preset`` files from
   ``templates/presets/``) into ``<target>/.claude/settings.json``:
   - allow / ask / deny rules are added if missing; existing rules are kept
     and never reordered or removed
   - ``defaultMode`` is set only if the project has none (unless
     ``--no-accept-edits``)
   - the PreToolUse Bash hook is added once
   - the previous file is backed up as ``settings.json.bak-<timestamp>``
4. Adds ``.sdlc/`` and ``.worktrees/`` to ``.gitignore`` in the target (if it is
   a git repo) and in every immediate sub-directory that is a git repo.

``settings.local.json`` is never touched: it holds personal rules.

Exit codes: 0 success, 1 a step was skipped because of a conflict (re-run with
``--force`` to replace conflicting symlinks), 2 bad arguments.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

REPO = Path(__file__).resolve().parent
SKILLS_SRC = REPO / ".claude" / "skills"
HOOKS_SRC = REPO / ".claude" / "hooks"
HOOK_SCRIPT = "approve-readonly-bash.py"
TEMPLATE = REPO / "templates" / "project-settings.json"
PRESETS_DIR = REPO / "templates" / "presets"
GITIGNORE_ENTRIES = (".sdlc/", ".worktrees/")
RULE_LISTS = ("allow", "ask", "deny")


class Installer:
    def __init__(self, target: Path, dry_run: bool, force: bool) -> None:
        self.target = target
        self.dry_run = dry_run
        self.force = force
        self.conflicts = 0

    # -- output -------------------------------------------------------------

    def say(self, status: str, message: str) -> None:
        prefix = "[dry-run] " if self.dry_run and status not in ("ok", "skip") else ""
        print(f"  {prefix}{status:<8} {message}")

    def conflict(self, message: str) -> None:
        self.conflicts += 1
        self.say("CONFLICT", message)

    # -- symlinks -----------------------------------------------------------

    def link(self, src: Path, dest: Path) -> None:
        """Make ``dest`` a symlink to ``src``; never replace real files."""
        rel = dest.relative_to(self.target)
        if dest.is_symlink():
            if Path(os.readlink(dest)) == src or dest.resolve() == src.resolve():
                self.say("ok", f"{rel} already links to {src}")
                return
            if not self.force:
                self.conflict(f"{rel} links to {os.readlink(dest)}; use --force to repoint it")
                return
            self.say("relink", f"{rel} -> {src}")
            if not self.dry_run:
                dest.unlink()
                dest.symlink_to(src)
            return
        if dest.exists():
            self.conflict(f"{rel} exists and is not a symlink; leaving it alone")
            return
        self.say("link", f"{rel} -> {src}")
        if not self.dry_run:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.symlink_to(src)

    def install_skills(self) -> None:
        print("Skills")
        for skill in sorted(SKILLS_SRC.glob("0*")):
            if (skill / "skill.md").is_file():
                self.link(skill, self.target / ".claude" / "skills" / skill.name)

    def install_hook(self) -> None:
        print("Hook")
        dest = self.target / ".claude" / "hooks"
        if dest.exists() and not dest.is_symlink() and dest.is_dir():
            # The project has its own hooks; link just our script into it.
            self.link(HOOKS_SRC / HOOK_SCRIPT, dest / HOOK_SCRIPT)
        else:
            self.link(HOOKS_SRC, dest)

    # -- settings -----------------------------------------------------------

    @staticmethod
    def load_json(path: Path) -> dict:
        with path.open(encoding="utf-8") as fh:
            return json.load(fh)

    def build_wanted(self, presets: List[str], accept_edits: bool) -> dict:
        template = self.load_json(TEMPLATE)
        perms = template.get("permissions", {})
        wanted = {name: list(perms.get(name, [])) for name in RULE_LISTS}
        # Skills and the hook are symlinks into this checkout, so reads resolve
        # outside the target project; allow reading this repo (and only it).
        wanted["allow"].append(f"Read(/{REPO.resolve()}/**)")
        for preset in presets:
            data = self.load_json(PRESETS_DIR / f"{preset}.json")
            for name in RULE_LISTS:
                wanted[name].extend(r for r in data.get(name, []) if r not in wanted[name])
        return {
            "rules": wanted,
            "defaultMode": perms.get("defaultMode") if accept_edits else None,
            "hooks": template.get("hooks", {}).get("PreToolUse", []),
        }

    @staticmethod
    def has_our_hook(settings: dict) -> bool:
        for group in settings.get("hooks", {}).get("PreToolUse", []):
            for hook in group.get("hooks", []):
                if HOOK_SCRIPT in hook.get("command", ""):
                    return True
        return False

    def merge(self, settings: dict, wanted: dict) -> List[str]:
        """Merge ``wanted`` into ``settings`` in place; return change notes."""
        notes: List[str] = []
        perms = settings.setdefault("permissions", {})
        for name in RULE_LISTS:
            current = perms.setdefault(name, [])
            added = [r for r in wanted["rules"][name] if r not in current]
            if added:
                current.extend(added)
                notes.append(f"added {len(added)} {name} rule(s)")
        # A rule in both allow and ask would be ambiguous to read; ask wins in
        # Claude Code anyway, so drop the allow copy of any ask rule we manage.
        overlap = [r for r in perms["allow"] if r in wanted["rules"]["ask"]]
        if overlap:
            perms["allow"] = [r for r in perms["allow"] if r not in overlap]
            notes.append(f"moved {len(overlap)} rule(s) from allow to ask")
        if wanted["defaultMode"] and "defaultMode" not in perms:
            perms["defaultMode"] = wanted["defaultMode"]
            notes.append(f"set defaultMode to {wanted['defaultMode']}")
        if not self.has_our_hook(settings):
            settings.setdefault("hooks", {}).setdefault("PreToolUse", []).extend(wanted["hooks"])
            notes.append("registered the PreToolUse Bash hook")
        return notes

    def install_settings(self, presets: List[str], accept_edits: bool) -> None:
        print("Settings")
        path = self.target / ".claude" / "settings.json"
        rel = path.relative_to(self.target)
        if path.exists():
            try:
                settings = self.load_json(path)
            except json.JSONDecodeError as exc:
                self.conflict(f"{rel} is not valid JSON ({exc}); fix it and re-run")
                return
        else:
            settings = {}
        notes = self.merge(settings, self.build_wanted(presets, accept_edits))
        if not notes:
            self.say("ok", f"{rel} already has every template rule and the hook")
            return
        for note in notes:
            self.say("update", f"{rel}: {note}")
        if self.dry_run:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            backup = path.with_name(f"settings.json.bak-{time.strftime('%Y%m%d-%H%M%S')}")
            shutil.copy2(path, backup)
            self.say("backup", f"previous file saved as {backup.relative_to(self.target)}")
        path.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")

    # -- gitignore ----------------------------------------------------------

    @staticmethod
    def is_git_repo(path: Path) -> bool:
        """A real repo has .git/HEAD; a worktree or submodule has a .git file.

        A stray .git folder without HEAD (left behind by some tools) is not a
        repository, and git itself ignores it, so it is skipped here too.
        """
        dot_git = path / ".git"
        return dot_git.is_file() or (dot_git / "HEAD").is_file()

    def git_repos(self) -> List[Path]:
        repos = [self.target] if self.is_git_repo(self.target) else []
        repos += sorted(p for p in self.target.iterdir() if p.is_dir() and self.is_git_repo(p))
        return repos

    def install_gitignores(self) -> None:
        print("Gitignore")
        repos = self.git_repos()
        if not repos:
            self.say("skip", "no git repo in the target or its immediate sub-directories")
            return
        for repo in repos:
            path = repo / ".gitignore"
            rel = path.relative_to(self.target)
            text = path.read_text(encoding="utf-8") if path.exists() else ""
            lines = {line.strip() for line in text.splitlines()}
            missing = [e for e in GITIGNORE_ENTRIES if e not in lines]
            if not missing:
                self.say("ok", f"{rel} already ignores {', '.join(GITIGNORE_ENTRIES)}")
                continue
            self.say("update", f"{rel}: add {', '.join(missing)}")
            if self.dry_run:
                continue
            if text and not text.endswith("\n"):
                text += "\n"
            path.write_text(text + "".join(e + "\n" for e in missing), encoding="utf-8")


def available_presets() -> List[str]:
    return sorted(p.stem for p in PRESETS_DIR.glob("*.json"))


def parse_args(argv: Optional[List[str]]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Install the SDLC skills, permission hook and permission rules into a project.",
    )
    parser.add_argument("target", help="path to the project to install into")
    parser.add_argument("--preset", action="append", default=[], choices=available_presets(),
                        help="add a tooling rule preset from templates/presets (repeatable)")
    parser.add_argument("--dry-run", action="store_true", help="print what would change, write nothing")
    parser.add_argument("--force", action="store_true", help="repoint symlinks that point somewhere else")
    parser.add_argument("--no-accept-edits", action="store_true",
                        help="do not set defaultMode to acceptEdits")
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    target = Path(args.target).expanduser().resolve()
    if not target.is_dir():
        print(f"error: {target} is not a directory", file=sys.stderr)
        return 2
    if target == REPO:
        print("error: target is the sdlc-markdown repo itself", file=sys.stderr)
        return 2

    print(f"Installing SDLC skills from {REPO}\n                      into {target}"
          + ("  (dry run)" if args.dry_run else ""))
    installer = Installer(target, dry_run=args.dry_run, force=args.force)
    installer.install_skills()
    installer.install_hook()
    installer.install_settings(args.preset, accept_edits=not args.no_accept_edits)
    installer.install_gitignores()

    print()
    if installer.conflicts:
        print(f"Finished with {installer.conflicts} conflict(s); see CONFLICT lines above.")
        return 1
    print("Done. Restart any Claude Code session open in the project, then follow")
    print("'Verify the install' in .claude/skills/README.md.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
