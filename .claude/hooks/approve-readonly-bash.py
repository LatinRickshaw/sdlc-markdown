#!/usr/bin/env python3
"""PreToolUse hook: auto-approve Bash commands that are provably read-only.

Claude Code already runs a built-in set of read-only commands (ls, cat, grep,
git log, ...) without a prompt, but it still prompts for shapes the SDLC skills
produce all the time in a multi-repo folder:

- ``cd <sub-repo> && git log ...``   (git after a cd into another directory)
- ``for r in a b; do grep ... ; done`` (control flow)
- ``sed -n '1,80p' f; git show HEAD --stat; yarn --version``
- anything the built-in parser gives up on (odd quoting, long pipelines)

This hook re-parses the command with ``shlex`` and answers ``"allow"`` only when
*every* segment is a read-only command from the allow-list below, every ``cd``
and ``git -C`` path stays inside the project, and nothing can write, execute
or escape (no ``$(...)``, backticks, heredocs, subshells, file redirects, exec
flags, ...).

Contract (fail closed):
  * allow  -> print the PreToolUse JSON decision and exit 0
  * unsure -> print nothing and exit 0, so the call goes through the normal
              permission flow (rules, then the user).  The hook never denies.
  * any exception -> treated as "unsure".

``deny`` and ``ask`` permission rules are still evaluated by Claude Code even
when this hook says allow, so a ``Bash(git push --force*)`` ask rule holds.

Debugging: set ``SDLC_HOOK_DEBUG=1`` to get a trace on stderr.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import sys
from typing import List, Optional, Sequence, Tuple

MAX_COMMAND_LENGTH = 10_000

# Tokens produced by shlex(punctuation_chars=True) that separate commands.
SEPARATORS = {"&&", "||", ";", ";;", "|", "|&", "&"}

# Any of these anywhere in the raw command text -> unsure.
FORBIDDEN_SUBSTRINGS = ("$(", "`", "<<", "<(", ">(", "\n", "\r")

# Shell words that never need checking on their own.
CONTROL_WORDS = {"do", "done", "then", "else", "elif", "fi", "esac", "!"}

# Environment assignments that are harmless in front of a read-only command.
SAFE_ASSIGNMENTS = {"LC_ALL", "LANG", "TZ", "NODE_ENV", "CI", "NO_COLOR", "TERM", "PAGER", "GIT_PAGER", "FORCE_COLOR"}
SAFE_ASSIGNMENT_VALUES_FOR_PAGER = {"cat", "", "less"}

# Loop/assignment variable names that must never be touched.
PROTECTED_VARS_PREFIXES = ("LD_", "DYLD_", "GIT_", "BASH_", "ZSH_")
PROTECTED_VARS = {"PATH", "IFS", "HOME", "PS4", "PROMPT_COMMAND", "ENV", "CDPATH", "SHELL", "EDITOR", "VISUAL", "PAGER", "GIT_PAGER"}

# Commands that are read-only with any flags (redirects are handled separately).
PLAIN_SAFE = {
    "ls", "cat", "echo", "printf", "pwd", "head", "tail", "grep", "egrep", "fgrep",
    "wc", "which", "diff", "stat", "du", "basename", "dirname", "realpath",
    "readlink", "true", "false", "type", "column", "nl", "tac", "rev", "fold",
    "comm", "paste", "seq", "cut", "tr", "uniq", "jq", "test", "[", "[[", "md5",
    "shasum", "sha256sum", "md5sum", "hostname", "uname", "whoami", "id", "env",
}

# Commands with write- or exec-capable flags; unquoted globs are refused for these
# because a glob could expand to a flag such as ``-delete``.
WRITE_CAPABLE = {"find", "sort", "sed", "awk", "git", "xargs", "rm", "yarn", "npm", "npx", "docker", "cd", "date", "say", "tree", "file", "rg", "corepack"}

FIND_FORBIDDEN = {"-exec", "-execdir", "-ok", "-okdir", "-delete", "-fprint", "-fprint0", "-fprintf", "-fls", "-files0-from"}

GIT_READONLY_SUBCOMMANDS = {
    "log", "show", "diff", "status", "branch", "worktree", "rev-parse", "ls-files",
    "blame", "shortlog", "describe", "remote", "tag", "stash", "cat-file", "show-ref",
    "ls-remote", "config", "rev-list", "name-rev", "merge-base", "diff-tree",
    "ls-tree", "var", "version", "--version", "count-objects", "check-ignore", "grep",
}
GIT_BRANCH_FORBIDDEN = {"-d", "-D", "-m", "-M", "-c", "-C", "-f", "--force", "--delete", "--move", "--copy",
                        "-u", "--set-upstream-to", "--unset-upstream", "--edit-description", "--track", "-t"}
GIT_BRANCH_LISTING_FLAGS = {"--list", "--contains", "--no-contains", "--merged", "--no-merged", "--points-at", "--format", "--sort"}

YARN_READONLY = ("--version", "-v", "why", "info", "list", "audit", "config get", "npm audit", "npm info", "workspaces list", "--help")
NPM_READONLY = ("--version", "-v", "view", "info", "show", "ls", "list", "audit", "outdated", "why", "explain", "search", "--help")
DOCKER_READONLY = {"ps", "images", "info", "version", "inspect", "--version"}
DOCKER_FORBIDDEN_FLAGS = ("-H", "--host", "--context", "--url", "--connection")

SED_PRINT_RANGE = re.compile(r"^(\d+|\$|/[^/]*/)(,(\d+|\$|/[^/]*/))?p$")
VAR_ASSIGNMENT = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$")


class Unsure(Exception):
    """Raised whenever the command cannot be proven read-only."""


def _debug(msg: str) -> None:
    if os.environ.get("SDLC_HOOK_DEBUG"):
        sys.stderr.write(f"[approve-readonly-bash] {msg}\n")


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def tokenize(command: str) -> List[str]:
    lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    lexer.commenters = ""  # the shell treats a mid-word '#' literally; never hide text after it
    try:
        return list(lexer)
    except ValueError as exc:  # unbalanced quotes
        raise Unsure(f"unparseable: {exc}") from exc


def has_unquoted(command: str, chars: str) -> bool:
    """True if any of ``chars`` appears outside single/double quotes."""
    in_single = in_double = False
    escaped = False
    for ch in command:
        if escaped:
            escaped = False
            continue
        if ch == "\\" and not in_single:
            escaped = True
            continue
        if ch == "'" and not in_double:
            in_single = not in_single
            continue
        if ch == '"' and not in_single:
            in_double = not in_double
            continue
        if not in_single and not in_double and ch in chars:
            return True
    return False


def raw_segments(command: str) -> List[str]:
    """Split the raw command on shell separators that sit outside quotes.

    Mirrors split_segments() but keeps the original text, so quoting can be
    inspected per segment (shlex strips quotes from its tokens).
    """
    parts: List[str] = []
    buf: List[str] = []
    in_single = in_double = False
    escaped = False
    i = 0
    while i < len(command):
        ch = command[i]
        if escaped:
            buf.append(ch)
            escaped = False
            i += 1
            continue
        if ch == "\\" and not in_single:
            buf.append(ch)
            escaped = True
            i += 1
            continue
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif not in_single and not in_double:
            two = command[i:i + 2]
            if two in ("&&", "||", ";;", "|&"):
                parts.append("".join(buf))
                buf = []
                i += 2
                continue
            if ch in ";|&":
                parts.append("".join(buf))
                buf = []
                i += 1
                continue
        buf.append(ch)
        i += 1
    parts.append("".join(buf))
    return [p for p in (x.strip() for x in parts) if p]


def split_segments(tokens: Sequence[str]) -> List[List[str]]:
    segments: List[List[str]] = []
    current: List[str] = []
    for tok in tokens:
        if tok in SEPARATORS:
            if current:
                segments.append(current)
            current = []
        else:
            current.append(tok)
    if current:
        segments.append(current)
    return segments


def strip_redirects(tokens: List[str]) -> List[str]:
    """Remove redirect tokens; only /dev/null and fd duplication are allowed."""
    out: List[str] = []
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok in (">", ">>", "&>", "&>>", ">|"):
            target = tokens[i + 1] if i + 1 < len(tokens) else ""
            if target != "/dev/null":
                raise Unsure(f"redirect to {target or 'nothing'}")
            # drop a preceding bare fd number such as the ``2`` in ``2>/dev/null``
            if out and out[-1].isdigit():
                out.pop()
            i += 2
            continue
        if tok in (">&", "&>&"):
            target = tokens[i + 1] if i + 1 < len(tokens) else ""
            if target not in ("1", "2"):
                raise Unsure(f"redirect >&{target}")
            if out and out[-1].isdigit():
                out.pop()
            i += 2
            continue
        if tok == "<":
            # input redirect from a file: read-only, keep the file as an argument
            i += 1
            continue
        if tok and all(c in "();<>|&" for c in tok):
            # a bare operator token shlex split out, such as "(" or ">|"
            raise Unsure(f"shell operator {tok!r}")
        out.append(tok)
        i += 1
    return out


def resolve_inside(path: str, cwd: str, project_dir: str) -> str:
    if not path or path.startswith("-") or "$" in path or path.startswith("~"):
        raise Unsure(f"cannot resolve path {path!r}")
    resolved = os.path.realpath(os.path.join(cwd, path))
    root = os.path.realpath(project_dir)
    if resolved != root and not resolved.startswith(root + os.sep):
        raise Unsure(f"path {path!r} is outside the project")
    return resolved


# ---------------------------------------------------------------------------
# Per-command checks.  Each returns a short label for the decision reason.
# ---------------------------------------------------------------------------

def check_git(args: List[str], cwd: str, project_dir: str) -> str:
    i = 0
    while i < len(args) and args[i].startswith("-") and args[i] not in GIT_READONLY_SUBCOMMANDS:
        opt = args[i]
        if opt == "-C":
            if i + 1 >= len(args):
                raise Unsure("git -C without path")
            resolve_inside(args[i + 1], cwd, project_dir)
            i += 2
            continue
        if opt in ("--no-pager", "-P"):
            i += 1
            continue
        raise Unsure(f"git global option {opt}")
    if i >= len(args):
        raise Unsure("git without subcommand")
    sub = args[i]
    rest = args[i + 1:]
    if sub not in GIT_READONLY_SUBCOMMANDS:
        raise Unsure(f"git {sub} is not read-only")
    for a in rest:
        if a.startswith("--output") or a in ("--ext-diff", "--textconv") or a.startswith("--exec"):
            raise Unsure(f"git {sub} {a}")
    if sub == "branch":
        for a in rest:
            if a in GIT_BRANCH_FORBIDDEN:
                raise Unsure(f"git branch {a}")
        positional = [a for a in rest if not a.startswith("-")]
        listing = any(a.split("=")[0] in GIT_BRANCH_LISTING_FLAGS for a in rest)
        if positional and not listing:
            raise Unsure("git branch <name> creates a branch")
    elif sub == "grep":
        # -O / --open-files-in-pager runs an arbitrary program on the matches
        if any(a.startswith("-O") or a.startswith("--open-files-in-pager") for a in rest):
            raise Unsure("git grep -O runs a pager")
    elif sub == "worktree":
        if rest[:1] != ["list"]:
            raise Unsure("git worktree is only read-only for list")
    elif sub == "remote":
        if rest and rest[0] not in ("-v", "--verbose", "show", "get-url"):
            raise Unsure(f"git remote {rest[0]}")
    elif sub == "tag":
        if rest and not all(a in ("-l", "--list", "-n") or a.startswith("-n") or a.startswith("--sort") or a.startswith("--contains") or not a.startswith("-") and any(x in ("-l", "--list") for x in rest) for a in rest):
            raise Unsure("git tag with non-listing arguments")
    elif sub == "stash":
        if rest[:1] not in (["list"], ["show"]):
            raise Unsure("git stash is only read-only for list/show")
    elif sub == "config":
        if not rest or rest[0] not in ("--get", "--get-all", "--list", "-l", "--get-regexp"):
            raise Unsure("git config without a read flag")
    return f"git {sub}"


def check_find(args: List[str]) -> str:
    for a in args:
        if a in FIND_FORBIDDEN:
            raise Unsure(f"find {a}")
    return "find"


def check_sed(args: List[str]) -> str:
    flags = [a for a in args if a.startswith("-")]
    scripts: List[str] = []
    i = 0
    seen_n = False
    while i < len(args):
        a = args[i]
        if a in ("-n", "--quiet", "--silent"):
            seen_n = True
        elif a in ("-e", "--expression"):
            if i + 1 >= len(args):
                raise Unsure("sed -e without script")
            scripts.append(args[i + 1])
            i += 2
            continue
        elif a.startswith("-") and a != "--":
            if "i" in a or "f" in a or a.startswith("--in-place") or a.startswith("--file"):
                raise Unsure(f"sed {a}")
            if "n" in a:
                seen_n = True
        elif not scripts:
            scripts.append(a)
        i += 1
    if not seen_n:
        raise Unsure("sed without -n")
    if not scripts:
        raise Unsure("sed without script")
    for s in scripts:
        if not SED_PRINT_RANGE.match(s):
            raise Unsure(f"sed script {s!r} is not a plain print range")
    _ = flags
    return "sed -n"


def check_awk(args: List[str]) -> str:
    for a in args:
        if a in ("-f", "--file", "-e", "--source", "-i", "--include", "-l", "--load"):
            raise Unsure(f"awk {a}")
        if any(bad in a for bad in ("system(", "getline", ">", "|", "close(", "fflush", "ENVIRON")):
            raise Unsure("awk script can write or execute")
    return "awk"


def check_sort(args: List[str]) -> str:
    for a in args:
        if a in ("-o", "--output") or a.startswith("--output=") or a.startswith("--compress-program") or a.startswith("-o"):
            raise Unsure(f"sort {a}")
    return "sort"


def check_simple_with_forbidden(name: str, args: List[str], forbidden: Sequence[str]) -> str:
    for a in args:
        for f in forbidden:
            if a == f or a.startswith(f + "="):
                raise Unsure(f"{name} {a}")
    return name


def check_yarn(args: List[str], cwd: str, project_dir: str) -> str:
    if args[:1] == ["--cwd"]:
        if len(args) < 2:
            raise Unsure("yarn --cwd without path")
        resolve_inside(args[1], cwd, project_dir)
        args = args[2:]
    joined = " ".join(args)
    for ro in YARN_READONLY:
        if joined == ro or joined.startswith(ro + " "):
            if "fix" in args:
                raise Unsure("yarn audit fix")
            return f"yarn {ro}"
    raise Unsure(f"yarn {joined} is not read-only")


def check_npm(args: List[str]) -> str:
    joined = " ".join(args)
    for ro in NPM_READONLY:
        if joined == ro or joined.startswith(ro + " "):
            if "fix" in args:
                raise Unsure("npm audit fix")
            return f"npm {ro}"
    raise Unsure(f"npm {joined} is not read-only")


def check_docker(args: List[str]) -> str:
    for a in args:
        if a in DOCKER_FORBIDDEN_FLAGS or a.startswith(tuple(f + "=" for f in DOCKER_FORBIDDEN_FLAGS)):
            raise Unsure(f"docker {a}")
    if not args or args[0] not in DOCKER_READONLY:
        raise Unsure("docker subcommand is not read-only")
    return f"docker {args[0]}"


def check_segment(tokens: List[str], state: dict) -> str:
    """Validate one pipeline segment; returns a label. Mutates state['cwd'] on cd."""
    tokens = strip_redirects(tokens)
    if not tokens:
        return "empty"

    # Control-flow prefixes and standalone keywords
    if tokens[0] == "for":
        if len(tokens) < 3 or tokens[2] != "in":
            raise Unsure("unrecognised for loop")
        var = tokens[1]
        if var in PROTECTED_VARS or var.startswith(PROTECTED_VARS_PREFIXES):
            raise Unsure(f"loop over protected variable {var}")
        return "for"
    if tokens[0] in ("while", "until", "if", "elif"):
        tokens = tokens[1:]
    while tokens and tokens[0] in CONTROL_WORDS:
        tokens = tokens[1:]
    if not tokens:
        return "control"

    # Leading environment assignments
    while tokens and VAR_ASSIGNMENT.match(tokens[0]):
        name, value = VAR_ASSIGNMENT.match(tokens[0]).groups()
        if name in PROTECTED_VARS and name not in ("PAGER", "GIT_PAGER"):
            raise Unsure(f"assignment to {name}")
        if name.startswith(PROTECTED_VARS_PREFIXES) and name != "GIT_PAGER":
            raise Unsure(f"assignment to {name}")
        if name not in SAFE_ASSIGNMENTS:
            raise Unsure(f"assignment to {name}")
        if name in ("PAGER", "GIT_PAGER") and value not in SAFE_ASSIGNMENT_VALUES_FOR_PAGER:
            raise Unsure(f"{name}={value}")
        tokens = tokens[1:]
    if not tokens:
        return "assignment"

    # Wrappers
    if tokens[0] == "timeout":
        tokens = tokens[2:] if len(tokens) > 2 else []
    elif tokens[0] in ("time", "command", "builtin", "noglob"):
        tokens = tokens[1:]
    if not tokens:
        raise Unsure("wrapper without command")

    cmd, args = tokens[0], tokens[1:]
    if cmd.startswith("$") or "/" in cmd and cmd not in ("/usr/bin/jq",):
        raise Unsure(f"command word {cmd!r} not allowed")

    cwd, project_dir = state["cwd"], state["project_dir"]

    if cmd == "cd":
        if not args or len(args) > 1:
            raise Unsure("cd without a single path")
        state["cwd"] = resolve_inside(args[0], cwd, project_dir)
        return "cd"
    if cmd == "git":
        return check_git(args, cwd, project_dir)
    if cmd == "find":
        return check_find(args)
    if cmd == "sed":
        return check_sed(args)
    if cmd == "awk":
        return check_awk(args)
    if cmd == "sort":
        return check_sort(args)
    if cmd == "xargs":
        if not args or args[0].startswith("-"):
            raise Unsure("xargs with flags")
        return "xargs " + check_segment(args, state)
    if cmd == "yarn":
        return check_yarn(args, cwd, project_dir)
    if cmd == "corepack":
        if args[:1] != ["yarn"]:
            raise Unsure("corepack is only read-only for yarn read-only subcommands")
        return "corepack " + check_yarn(args[1:], cwd, project_dir)
    if cmd == "npm":
        return check_npm(args)
    if cmd == "node":
        if args in (["--version"], ["-v"]):
            return "node --version"
        raise Unsure("node runs code")
    if cmd in ("python3", "python"):
        if args in (["--version"], ["-V"]):
            return f"{cmd} --version"
        raise Unsure(f"{cmd} runs code")
    if cmd == "docker":
        return check_docker(args)
    if cmd == "wrangler":
        if args in (["--version"], ["-v"]):
            return "wrangler --version"
        raise Unsure("wrangler is not read-only")
    if cmd == "date":
        return check_simple_with_forbidden("date", args, ("-s", "--set"))
    if cmd == "say":
        return check_simple_with_forbidden("say", args, ("-o", "--output-file"))
    if cmd == "tree":
        return check_simple_with_forbidden("tree", args, ("-o",))
    if cmd == "file":
        return check_simple_with_forbidden("file", args, ("-m", "--magic-file", "-f", "--files-from"))
    if cmd == "rg":
        return check_simple_with_forbidden("rg", args, ("--pre", "--pre-glob"))
    if cmd == "env":
        if args:
            raise Unsure("env with arguments")
        return "env"
    if cmd == "which":
        return check_simple_with_forbidden("which", args, ("-i", "--read-alias", "--read-functions"))
    if cmd in PLAIN_SAFE:
        return cmd
    raise Unsure(f"{cmd} is not in the read-only allow-list")


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------

def decide(command: str, project_dir: str, cwd: Optional[str] = None) -> Optional[str]:
    """Return a reason string if the command is provably read-only, else None."""
    try:
        if not command or len(command) > MAX_COMMAND_LENGTH:
            raise Unsure("empty or too long")
        for bad in FORBIDDEN_SUBSTRINGS:
            if bad in command:
                raise Unsure(f"contains {bad!r}")
        tokens = tokenize(command)
        segments = split_segments(tokens)
        if not segments:
            raise Unsure("no command")
        raw = raw_segments(command)
        if len(raw) != len(segments):
            # Could not line the raw text up with the parsed segments; be
            # conservative and treat a glob anywhere as tainting every segment.
            raw = [command] * len(segments)
        state = {"cwd": os.path.realpath(cwd or project_dir), "project_dir": project_dir}
        labels: List[str] = []
        for seg, raw_seg in zip(segments, raw):
            first = next((t for t in seg if t not in CONTROL_WORDS), "")
            if first in WRITE_CAPABLE and has_unquoted(raw_seg, "*?["):
                raise Unsure(f"unquoted glob with {first}")
            labels.append(check_segment(list(seg), state))
        reason = "sdlc read-only hook: " + ", ".join(dict.fromkeys(labels))
        return reason[:300]
    except Unsure as exc:
        _debug(f"unsure ({exc}): {command!r}")
        return None


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    if payload.get("tool_name") != "Bash":
        return 0
    command = (payload.get("tool_input") or {}).get("command") or ""
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR") or payload.get("cwd") or os.getcwd()
    cwd = payload.get("cwd") or project_dir
    try:
        reason = decide(command, project_dir, cwd)
    except Exception as exc:  # never block on our own bugs
        _debug(f"error: {exc!r}")
        return 0
    if reason:
        _debug(f"allow: {command!r}")
        json.dump(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "allow",
                    "permissionDecisionReason": reason,
                }
            },
            sys.stdout,
        )
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
