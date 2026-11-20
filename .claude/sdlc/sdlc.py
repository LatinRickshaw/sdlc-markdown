#!/usr/bin/env python3
"""Deterministic helpers for the SDLC skills.

The skills are markdown run by an AI agent. Anything with exactly one correct
answer lives here instead, so the agent runs one command and branches on its
JSON output rather than re-deriving the logic from prose every time.

Run it from the project root (the directory the Claude session started in):

    python3 -I .claude/sdlc/sdlc.py state init SOC-15 --jira-server mcp__Atlassian__ --cloud-id <id>
    python3 -I .claude/sdlc/sdlc.py state locate SOC-15 --stage 03
    python3 -I .claude/sdlc/sdlc.py state advance SOC-15 03
    python3 -I .claude/sdlc/sdlc.py state halt SOC-15 03 --reason "2 tests still failing"

``state`` owns the pipeline state file ``.sdlc/<JIRA-KEY>.json``: creating it,
validating chained mode, advancing or halting a stage, and the Finished /
Halted announcements. The agent never edits ``stages``, ``current_stage``,
``halted``, ``completed_at`` or ``notes`` by hand.

Output contract: one JSON object on stdout.
  exit 0  ok (``locate`` also exits 0 for standalone mode; read ``mode``)
  exit 1  refused or gate failed; ``reason`` says why
  exit 2  usage error (argparse)

Stdlib only; safe to run with ``python3 -I``. Set ``SDLC_NO_SAY=1`` to skip the
spoken ``say`` announcements (tests do).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, List, Optional, Tuple

STAGES = {
    "01": "01-investigate-task",
    "02": "02-start-task",
    "03": "03-dev-execute",
    "04": "04-reconcile-work",
    "05": "05-create-pr",
    "06": "06-pr-review",
    "07": "07-complete-task",
}
ORDER = list(STAGES)
STATE_DIR = ".sdlc"
JIRA_SERVERS = ("mcp__Atlassian__", "mcp__claude_ai_Atlassian_MCP__")
KEY_RE = re.compile(r"^[A-Z][A-Z0-9_]*-[0-9]+$")
UNTIL_07_WARNING = (
    '⚠️  --until 07 will MERGE the pull request(s) and transition the Jira ticket to "Done" without pausing.'
)


class Refused(Exception):
    """A request the state machine will not carry out (exit 1)."""

    def __init__(self, reason: str, **extra) -> None:
        super().__init__(reason)
        self.payload = {"ok": False, "reason": reason, **extra}


# -- helpers ----------------------------------------------------------------


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def emit(payload: dict, code: int = 0) -> int:
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return code


def announce(text: str) -> None:
    """Speak ``text`` with macOS ``say``; silently skip where unavailable."""
    if os.environ.get("SDLC_NO_SAY") == "1":
        return
    try:
        subprocess.run(["say", text], check=False, timeout=30,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except (OSError, subprocess.SubprocessError):
        pass


def one_line(text: str) -> str:
    return " ".join(text.split())


def search_dirs(start: Path) -> Iterator[Path]:
    """``start`` and its ancestors, never above the project root.

    The bound is ``$CLAUDE_PROJECT_DIR`` when ``start`` is inside it, else the
    user's home directory, so an unrelated pipeline elsewhere is never found.
    """
    start = start.resolve()
    bound = None
    project = os.environ.get("CLAUDE_PROJECT_DIR")
    if project:
        candidate = Path(project).resolve()
        if start == candidate or candidate in start.parents:
            bound = candidate
    if bound is None:
        home = Path.home().resolve()
        bound = home if (start == home or home in start.parents) else Path(start.anchor)
    current = start
    while True:
        yield current
        if current == bound or current.parent == current:
            return
        current = current.parent


def find_state(key: str, start: Optional[Path] = None) -> Optional[Path]:
    for directory in search_dirs(start or Path.cwd()):
        path = directory / STATE_DIR / f"{key}.json"
        if path.is_file():
            return path
    return None


def load(path: Path) -> dict:
    with path.open(encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError("top level is not an object")
    return data


def save(path: Path, state: dict) -> None:
    """Write atomically so an interrupted run never leaves half a file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(state, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def check_key(key: str) -> None:
    if not KEY_RE.match(key):
        raise Refused(f"'{key}' is not a Jira key like SOC-15")


def stage_call(state: dict, num: str) -> dict:
    """The exact Skill tool call that runs stage ``num``."""
    args = state["jira_key"]
    if num == "02" and state.get("worktree"):
        args += " --worktree"
    return {"stage": num, "skill": STAGES[num], "args": args}


def summary_table(state: dict) -> str:
    rows = ["| Stage | Skill | Status |", "| ----- | ----- | ------ |"]
    for num in ORDER:
        status = state.get("stages", {}).get(num, {}).get("status", "?")
        rows.append(f"| {num} | /{STAGES[num]} | {status} |")
    return "\n".join(rows)


def open_chained(key: str, stage: Optional[str]) -> Tuple[Path, dict, Optional[str]]:
    """Locate and validate the state file.

    Returns ``(path, state, problem)``; ``problem`` is None when the file puts
    this invocation in chained mode (and, if ``stage`` is given, that stage is
    ``in_progress``). Raises Refused when there is no usable file at all.
    """
    path = find_state(key)
    if path is None:
        raise Refused(f"no state file .sdlc/{key}.json in this directory or its ancestors")
    try:
        state = load(path)
    except (OSError, ValueError) as exc:
        raise Refused(f"{path}: unreadable state file ({exc})", file=str(path))
    if state.get("jira_key") != key:
        return path, state, f"{path}: jira_key is {state.get('jira_key')!r}, not {key!r}"
    if state.get("mode") != "chained":
        return path, state, f"{path}: mode is {state.get('mode')!r}, not 'chained'"
    if stage is not None:
        status = state.get("stages", {}).get(stage, {}).get("status")
        if status != "in_progress":
            return path, state, f"{path}: stage {stage} is {status!r}, not 'in_progress'"
    return path, state, None


def finish(path: Path, state: dict) -> dict:
    key, until = state["jira_key"], state["until"]
    state["current_stage"] = None
    state["completed_at"] = now()
    save(path, state)
    announce(f"finished the SDLC pipeline for {key}")
    if until == "07":
        next_step = f"Pipeline finished. PR merged and {key} is Done."
    else:
        nxt = stage_call(state, ORDER[ORDER.index(until) + 1])
        what = "before merge" if until == "06" else f"after stage {until}"
        next_step = f"Pipeline finished {what}. When you are ready:\n  /{nxt['skill']} {nxt['args']}"
    return {
        "ok": True,
        "finished": True,
        "file": str(path),
        "message": f"{summary_table(state)}\n\n{next_step}",
    }


# -- state subcommands ------------------------------------------------------


def cmd_init(args: argparse.Namespace) -> int:
    key = args.jira_key
    check_key(key)
    first, last = args.from_stage, args.until
    if ORDER.index(first) > ORDER.index(last):
        raise Refused(f"--from {first} is after --until {last}")
    path = Path.cwd() / STATE_DIR / f"{key}.json"
    if path.exists():
        try:
            existing = load(path)
        except (OSError, ValueError):
            existing = {}
        current = existing.get("current_stage")
        raise Refused(
            "a pipeline state file already exists; refusing to start over it",
            file=str(path),
            current_stage=current,
            status=existing.get("stages", {}).get(current or "", {}).get("status"),
            halted=existing.get("halted"),
            options=[f"/00-run-sdlc {key} --resume", f"/00-run-sdlc {key} --reset", f"/00-run-sdlc {key} --status"],
        )
    warning = UNTIL_07_WARNING if last == "07" else None
    if args.check:
        return emit({"ok": True, "check": True, "file": str(path), "warning": warning})
    if not args.jira_server or not args.cloud_id:
        raise Refused("--jira-server and --cloud-id are required (from the preflight Jira lookup)")

    started = now()
    first_i, last_i = ORDER.index(first), ORDER.index(last)
    stages = {}
    for i, num in enumerate(ORDER):
        if i < first_i or i > last_i:
            stages[num] = {"status": "skipped"}
        elif num == first:
            stages[num] = {"status": "in_progress", "started_at": started}
        else:
            stages[num] = {"status": "pending"}
    state = {
        "jira_key": key,
        "mode": "chained",
        "from": first,
        "until": last,
        "worktree": not args.no_worktree,
        "pipeline_root": str(Path.cwd().resolve()),
        "started_at": started,
        "jira": {"server_prefix": args.jira_server, "cloud_id": args.cloud_id, "review_transition": None},
        "pr_template": args.pr_template,
        "repos": [],
        "current_stage": first,
        "stages": stages,
        "halted": None,
        "completed_at": None,
        "notes": [],
    }
    save(path, state)
    return emit({"ok": True, "file": str(path), "warning": warning, "next": stage_call(state, first)})


def cmd_status(args: argparse.Namespace) -> int:
    check_key(args.jira_key)
    path = find_state(args.jira_key)
    if path is None:
        raise Refused(f"no state file .sdlc/{args.jira_key}.json")
    state = load(path)
    current = state.get("current_stage")
    halted = state.get("halted")
    if halted:
        summary = f"halted at stage {halted.get('stage')}: {halted.get('reason')}"
    elif current:
        summary = f"stage {current} ({STAGES.get(current, '?')}) is {state['stages'][current]['status']}"
    else:
        summary = f"finished at {state.get('completed_at')}"
    return emit({"ok": True, "file": str(path), "summary": summary,
                 "table": summary_table(state), "state": state})


def cmd_resume(args: argparse.Namespace) -> int:
    key = args.jira_key
    check_key(key)
    path, state, problem = open_chained(key, None)
    if problem:
        raise Refused(problem, file=str(path))
    span = ORDER[ORDER.index(state["from"]): ORDER.index(state["until"]) + 1]
    todo = [n for n in span if state["stages"][n]["status"] not in ("done", "skipped")]
    if not todo:
        return emit({"ok": True, "finished": True, "file": str(path),
                     "message": f"Nothing to resume: every stage {span[0]}–{span[-1]} is done.\n\n{summary_table(state)}"})
    num = todo[0]
    entry = state["stages"][num]
    entry["status"] = "in_progress"
    entry["started_at"] = now()
    entry.pop("finished_at", None)
    state["current_stage"] = num
    state["halted"] = None
    state["completed_at"] = None
    save(path, state)
    return emit({"ok": True, "file": str(path), "next": stage_call(state, num)})


def cmd_reset(args: argparse.Namespace) -> int:
    check_key(args.jira_key)
    path = Path.cwd() / STATE_DIR / f"{args.jira_key}.json"
    existed = path.is_file()
    if existed:
        path.unlink()
    return emit({"ok": True, "file": str(path), "removed": existed})


def cmd_locate(args: argparse.Namespace) -> int:
    key, stage = args.jira_key, args.stage
    check_key(key)
    try:
        path, state, problem = open_chained(key, stage)
    except Refused as exc:
        return emit({"ok": True, "mode": "standalone", "reason": exc.payload["reason"],
                     "file": exc.payload.get("file")})
    if problem:
        return emit({"ok": True, "mode": "standalone", "reason": problem, "file": str(path), "stale": True})
    return emit({"ok": True, "mode": "chained", "file": str(path), "stage": stage,
                 "until": state["until"], "worktree": state.get("worktree"),
                 "jira": state.get("jira"), "repos": state.get("repos"),
                 "pr_template": state.get("pr_template")})


def cmd_advance(args: argparse.Namespace) -> int:
    key, num = args.jira_key, args.stage
    check_key(key)
    path, state, problem = open_chained(key, num)
    if problem:
        # Re-running advance after a compaction must not skip a stage: if this
        # stage is already done and the next one is running, repeat the answer.
        stages = state.get("stages", {})
        i = ORDER.index(num)
        nxt = ORDER[i + 1] if i + 1 < len(ORDER) else None
        if (state.get("jira_key") == key and state.get("mode") == "chained"
                and stages.get(num, {}).get("status") == "done"
                and nxt and state.get("current_stage") == nxt
                and stages.get(nxt, {}).get("status") == "in_progress"):
            return emit({"ok": True, "already_advanced": True, "file": str(path), "next": stage_call(state, nxt)})
        raise Refused(problem, file=str(path))
    entry = state["stages"][num]
    entry["status"] = "done"
    entry["finished_at"] = now()
    if num == state["until"]:
        return emit(finish(path, state))
    nxt = ORDER[ORDER.index(num) + 1]
    state["stages"][nxt].update({"status": "in_progress", "started_at": now()})
    state["current_stage"] = nxt
    save(path, state)
    return emit({"ok": True, "file": str(path), "next": stage_call(state, nxt)})


def load_advisory_diff(file: str) -> dict:
    try:
        with open(file, encoding="utf-8") as fh:
            diff = json.load(fh)
    except (OSError, ValueError) as exc:
        raise Refused(f"--advisory-diff {file}: {exc}")
    if not isinstance(diff, dict) or not diff:
        raise Refused("--advisory-diff must map repo names to {new, fixed, unchanged}")
    for repo, sets in diff.items():
        if not isinstance(sets, dict) or any(not isinstance(sets.get(k), list) for k in ("new", "fixed", "unchanged")):
            raise Refused(f"--advisory-diff: {repo!r} needs list values for new, fixed and unchanged")
    return diff


def cmd_halt(args: argparse.Namespace) -> int:
    key, num = args.jira_key, args.stage
    check_key(key)
    reason = one_line(args.reason)
    if not reason:
        raise Refused("--reason must not be empty")
    diff = load_advisory_diff(args.advisory_diff) if args.advisory_diff else None
    path, state, problem = open_chained(key, None)
    if problem:
        raise Refused(problem, file=str(path))
    status = state["stages"].get(num, {}).get("status")
    if status not in ("in_progress", "failed"):
        raise Refused(f"stage {num} is {status!r}; only a running stage can halt", file=str(path))
    state["stages"][num]["status"] = "failed"
    state["stages"][num]["finished_at"] = now()
    state["current_stage"] = num
    state["halted"] = {"stage": num, "reason": reason, "at": now()}
    if diff is not None:
        state["halted"]["advisory_diff"] = diff
    save(path, state)
    announce(f"the SDLC pipeline halted at stage {num} for {key}")
    message = (f"Pipeline halted at stage {num} (/{STAGES[num]}): {reason}\n\n"
               f"Fix the issue, then continue with:\n  /00-run-sdlc {key} --resume")
    return emit({"ok": True, "halted": True, "file": str(path), "message": message})


def cmd_note(args: argparse.Namespace) -> int:
    key = args.jira_key
    check_key(key)
    text = one_line(args.text)
    if not text:
        raise Refused("note text must not be empty")
    path, state, problem = open_chained(key, None)
    if problem:
        raise Refused(problem, file=str(path))
    state.setdefault("notes", []).append(text)
    save(path, state)
    return emit({"ok": True, "file": str(path), "notes": state["notes"]})


# -- CLI --------------------------------------------------------------------


def stage_arg(value: str) -> str:
    value = value.zfill(2)
    if value not in STAGES:
        raise argparse.ArgumentTypeError(f"stage must be one of {', '.join(ORDER)}")
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sdlc.py", description="Deterministic helpers for the SDLC skills.")
    groups = parser.add_subparsers(dest="group", required=True)

    state = groups.add_parser("state", help="pipeline state file .sdlc/<JIRA-KEY>.json")
    sub = state.add_subparsers(dest="command", required=True)

    p = sub.add_parser("init", help="validate arguments and create a new pipeline")
    p.add_argument("jira_key")
    p.add_argument("--from", dest="from_stage", type=stage_arg, default="01")
    p.add_argument("--until", type=stage_arg, default="06")
    p.add_argument("--no-worktree", action="store_true")
    p.add_argument("--jira-server", choices=JIRA_SERVERS)
    p.add_argument("--cloud-id")
    p.add_argument("--pr-template", default=None, help="path of the PR template, if any")
    p.add_argument("--check", action="store_true", help="validate only; write nothing")
    p.set_defaults(func=cmd_init)

    for name, func, text in (("status", cmd_status, "print the state and a one-line summary"),
                             ("resume", cmd_resume, "restart the first unfinished stage"),
                             ("reset", cmd_reset, "delete the state file")):
        p = sub.add_parser(name, help=text)
        p.add_argument("jira_key")
        p.set_defaults(func=func)

    p = sub.add_parser("locate", help="find the state file and decide chained vs standalone mode")
    p.add_argument("jira_key")
    p.add_argument("--stage", type=stage_arg, required=True)
    p.set_defaults(func=cmd_locate)

    p = sub.add_parser("advance", help="mark a stage done and name the next skill to invoke")
    p.add_argument("jira_key")
    p.add_argument("stage", type=stage_arg)
    p.set_defaults(func=cmd_advance)

    p = sub.add_parser("halt", help="mark a stage failed and stop the pipeline")
    p.add_argument("jira_key")
    p.add_argument("stage", type=stage_arg)
    p.add_argument("--reason", required=True)
    p.add_argument("--advisory-diff", help="JSON file: {repo: {new: [], fixed: [], unchanged: []}}")
    p.set_defaults(func=cmd_halt)

    p = sub.add_parser("note", help="append a non-blocking observation to notes")
    p.add_argument("jira_key")
    p.add_argument("text")
    p.set_defaults(func=cmd_note)
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except Refused as exc:
        return emit(exc.payload, 1)


if __name__ == "__main__":
    sys.exit(main())
