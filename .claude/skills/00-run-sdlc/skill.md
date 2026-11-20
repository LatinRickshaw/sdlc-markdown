# Run SDLC Pipeline Skill

Runs the SDLC skills `01` → `07` as one automated chain for a Jira ticket. By default it runs investigation through PR review (`01` → `06`) and **stops before merge**. Merging and closing the ticket (`07`) only happens when you explicitly pass `--until 07`.

Chained mode is recorded in a **state file on disk** (`.sdlc/<JIRA-KEY>.json`). Each stage skill reads that file at its end to decide whether to hand off to the next stage. Without the file, every skill behaves exactly as it does today: it stops and waits for you.

## Shell & Tool Conventions

These rules keep the skill runnable without permission prompts. Claude Code auto-approves only commands it can prove are read-only, and the project ships a PreToolUse hook that extends that proof; both are defeated by the shapes below.

- Prefer the `Read`, `Grep` and `Glob` tools over Bash `cat`, `grep`, `find` and `sed -n` **if they are listed** in this session; they never prompt inside the project. If `Glob`/`Grep` are not available, fall back to `ls -d */.git` (repo discovery), `ls <dir>`, `grep -n <pattern> <file>` and `git -C <repo> grep -n <pattern>` via Bash; all are auto-approved. Never call a tool that is not listed.
- **Never `cd <dir> && git …`.** Running git after a `cd` into another directory always prompts. Use `git -C <absolute-repo-path> <subcommand>`, one git operation per Bash call.
- No `for`/`while` loops over repos. Run one command per repo per Bash call; parallel calls are fine.
- JSON: `jq` only. Never `python3 -c` or `node -e`; inline scripts are arbitrary code and always prompt.
- No ad-hoc scripts either: never write a `.js`/`.ts`/`.py`/`.sh` file (scratchpad or elsewhere) and run it with `node`/`python3`/`bash`/`npx`. It is arbitrary code and always prompts. Checks that need code become tests in the repo's own suite, run through its test script (e.g. `yarn --cwd <repo> test <path>`).
- The one exception is the shipped pipeline script, `python3 -I .claude/sdlc/sdlc.py <group> <command> …`. It is allow-listed, prints one JSON object and exits 0 (ok), 1 (refused, see `reason`) or 2 (usage). Run it from the project root; if the shell is elsewhere, use `cd <project-root> && python3 -I .claude/sdlc/sdlc.py …`.
- No redirects to files except `2>/dev/null`. No `$(…)`, backticks, heredocs, `xargs` with flags, or `find -exec`/`-delete`.
- Reports and the state file's `repos`, `jira` and `pr_template` fields are written with the `Write`/`Edit` tools, never `cat <<EOF >` or `echo >`. Everything else in the state file is written only by the pipeline script.
- Temporary reports go in the session scratchpad directory, never in a repo.
- Security advisories and registry metadata via the `WebFetch` tool, never `curl`.
- Keep each command single-line with simple quoting; one job per call.

### Command shapes

Use exactly these shapes; each one matches a shipped permission rule, so any variation prompts. `<repo>` is an absolute repo or worktree path. The yarn flavour of each repo is recorded in the state file (`repos[].yarn`); without a state file, a repo with `.yarnrc.yml` or a `packageManager: "yarn@2+"` field is berry, otherwise classic.

| Action                                   | Shape                                                                                   |
| ---------------------------------------- | --------------------------------------------------------------------------------------- |
| install / build / test (yarn classic)    | `yarn --cwd <repo> install --frozen-lockfile`, `yarn --cwd <repo> build`, `yarn --cwd <repo> test` |
| install / build / test (yarn berry)      | `cd <repo> && corepack yarn install --immutable`, `cd <repo> && corepack yarn build`, `cd <repo> && corepack yarn test` (never `corepack yarn --cwd`: corepack picks the yarn version from the shell cwd) |
| first push of a branch                   | `git -C <repo> push -u origin <branch>`                                                 |
| every later push                         | `git -C <repo> push`                                                                    |
| bring main into the branch               | `git -C <repo> fetch origin main`, then `git -C <repo> merge origin/main --no-edit`     |
| wait for CI                              | GitHub MCP `pull_request_read` with method `get_check_runs`, polled after a background `sleep 90` (Bash `run_in_background`). Never the `gh` CLI. |

## Usage

```
/00-run-sdlc <JIRA-KEY> [--from NN] [--until NN] [--no-worktree] [--resume] [--reset] [--status]
```

### Examples

```bash
# Default: investigate → start → execute → reconcile → PR → review, then stop before merge
/00-run-sdlc SOC-15

# Skip investigation, stop after implementation
/00-run-sdlc SOC-15 --from 02 --until 03

# Full run including merge and Jira "Done" (prints a warning first)
/00-run-sdlc SOC-15 --until 07

# Work in-place on the current checkout instead of the default isolated worktree
/00-run-sdlc SOC-15 --no-worktree

# Continue a halted or interrupted pipeline from the first unfinished stage
/00-run-sdlc SOC-15 --resume

# Show the current pipeline state and stop
/00-run-sdlc SOC-15 --status

# Discard an existing pipeline state and start fresh
/00-run-sdlc SOC-15 --reset
```

## Arguments

| Argument     | Required | Default | Description                                                                 |
| ------------ | -------- | ------- | --------------------------------------------------------------------------- |
| `jira_key`   | Yes      | —       | The Jira issue key to run the pipeline for                                  |
| `--from NN`  | No       | `01`    | First stage to run (`01`–`07`)                                              |
| `--until NN` | No       | `06`    | Last stage to run (`01`–`07`). Must be ≥ `--from`. `07` merges and closes.  |
| `--no-worktree` | No    | off     | Work in-place instead of the default `.worktrees/<JIRA-KEY>` worktree       |
| `--resume`   | No       | off     | Continue an existing pipeline from the first stage that is not `done`       |
| `--reset`    | No       | off     | Delete the existing state file and start a new pipeline                     |
| `--status`   | No       | off     | Print the existing state file and stop                                      |

Stage numbers map to skills:

| NN   | Skill                  |
| ---- | ---------------------- |
| `01` | `/01-investigate-task` |
| `02` | `/02-start-task`       |
| `03` | `/03-dev-execute`      |
| `04` | `/04-reconcile-work`   |
| `05` | `/05-create-pr`        |
| `06` | `/06-pr-review`        |
| `07` | `/07-complete-task`    |

## What It Does

All state-file bookkeeping is done by the shipped script `python3 -I .claude/sdlc/sdlc.py state …`, run from the pipeline root (the current working directory). It validates arguments, writes the file, and prints one JSON object. Exit `1` means refused: print its `reason` and stop.

### 1. Status, Resume or Reset an Existing Pipeline

Handle these flags first; each one replaces steps 2–5:

| Flag       | Run                                                    | Then                                                                                                          |
| ---------- | ------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------- |
| `--status` | `python3 -I .claude/sdlc/sdlc.py state status <JIRA-KEY>` | Print its `summary` and `table`. **Stop.**                                                                    |
| `--resume` | `python3 -I .claude/sdlc/sdlc.py state resume <JIRA-KEY>` | It validates `jira_key`, finds the first stage (in `from`→`until` order) whose status is not `done` or `skipped`, sets it to `in_progress` and clears `halted`. Invoke the `next` skill it prints (step 6), or print its `message` if it says `finished`. |
| `--reset`  | `python3 -I .claude/sdlc/sdlc.py state reset <JIRA-KEY>`  | The file is deleted; continue with step 2 to create a new pipeline.                                          |

### 2. Validate Arguments (before anything is fetched)

```
python3 -I .claude/sdlc/sdlc.py state init <JIRA-KEY> [--from NN] [--until NN] [--no-worktree] --check
```

- The script checks that `<JIRA-KEY>` looks like a Jira key, that `--from` and `--until` are in `01`–`07` with `from ≤ until`, and that no state file exists yet. It writes nothing.
- If a state file already exists, it exits `1`. **Refuse.** Print the current stage and status and the `--resume`, `--reset` and `--status` options it lists. Do not run anything.
- Worktree mode is the **default**: `/02-start-task` is invoked with `--worktree` unless `--no-worktree` was given. The worktree is created under `.worktrees/<JIRA-KEY>` and removed by `/07-complete-task`.
- If `--until 07`, the output's `warning` is this. Print it, then continue (the user asked for it on the command line):

  ```
  ⚠️  --until 07 will MERGE the pull request(s) and transition the Jira ticket to "Done" without pausing.
  ```

### 3. Preflight (fail fast, before anything is posted to Jira)

1. **Jira reachable, and which server**: fetch the ticket with `mcp__Atlassian__getJiraIssue` first. If that server is missing or returns 404, retry once with the claude.ai connector (`mcp__claude_ai_Atlassian_MCP__getJiraIssue`, after `getAccessibleAtlassianResources` for the `cloudId`). Record the server that worked as `jira.server_prefix` (`mcp__Atlassian__` or `mcp__claude_ai_Atlassian_MCP__`) and its `jira.cloud_id`. Stop if neither finds the ticket.
2. **GitHub MCP available** (only if `until ≥ 05`): confirm the GitHub MCP Server tools are loaded. `/05-create-pr` refuses to fall back to the `gh` CLI, so stop now rather than after implementation. Do not check whether the `gh` CLI is installed; no stage uses it.
3. **Clean working tree** (only if `from ≤ 02`): discover repos with the `Glob` tool if it is listed, otherwise `ls -d */.git` (`*/.git` plus the current directory, same discovery as `/02-start-task`), then run `git -C <absolute-repo-path> status --short` once per repo, each in its own Bash call (no `cd`, no loops). Stop if any repo has uncommitted changes.
4. **Environment facts** (recorded once by step 4, so later stages never rediscover them):
   - `pr_template`: the path of `.github/pull_request_template.md` (or `PULL_REQUEST_TEMPLATE.md`) if one exists in a discovered repo, else none.
   - `jira.review_transition`: leave `null`; `/05-create-pr` fills it with the name of the "In Review" transition if the ticket offers one, or `"none"` if it does not.
   - `repos`: leave `[]`; `/01-investigate-task` fills it (or `/02-start-task` when the run starts at `02` or later).

### 4. Create the State File

Run this from the pipeline root with the facts from preflight. Never write the file with the `Write` tool or a shell redirect:

```
python3 -I .claude/sdlc/sdlc.py state init <JIRA-KEY> [--from NN] [--until NN] [--no-worktree] --jira-server <server_prefix> --cloud-id <cloud_id> [--pr-template <path>]
```

It writes `.sdlc/<JIRA-KEY>.json` (creating `.sdlc/` as needed), sets stage `from` to `in_progress`, and prints `next`, the Skill tool call for the first stage. The file looks like this:

```json
{
  "jira_key": "SOC-15",
  "mode": "chained",
  "from": "01",
  "until": "06",
  "worktree": true,
  "pipeline_root": "/absolute/path/to/cwd",
  "started_at": "2026-11-16T10:00:00Z",
  "jira": { "server_prefix": "mcp__Atlassian__", "cloud_id": "00000000-0000-0000-0000-000000000000", "review_transition": null },
  "pr_template": null,
  "repos": [],
  "current_stage": "01",
  "stages": {
    "01": { "status": "in_progress", "started_at": "2026-11-16T10:00:00Z" },
    "02": { "status": "pending" },
    "03": { "status": "pending" },
    "04": { "status": "pending" },
    "05": { "status": "pending" },
    "06": { "status": "pending" },
    "07": { "status": "skipped" }
  },
  "halted": null,
  "completed_at": null,
  "notes": []
}
```

Field rules:

- Stage `status` is one of `pending | in_progress | done | failed | skipped`
- Stages outside `from`–`until` are `skipped`
- `halted` is `null` or `{ "stage": "04", "reason": "…", "at": "…" }`. `/06-pr-review` may add `"advisory_diff": { "<repo>": { "new": [...], "fixed": [...], "unchanged": [...] } }` when it halts on a pre-existing audit failure; `/07-complete-task` reads it
- `tools`, `jira`, `pr_template` and `repos` are written once (preflight and `/01-investigate-task`). Stages `02`–`07` **read them from this file** instead of rediscovering them: use `jira.server_prefix` for every Atlassian call and pass `jira.cloud_id`; use `repos[].path` instead of scanning for `.git`; use `repos[].yarn` to pick the command shape. Each `repos` entry is `{ "name": "api", "path": "/abs/path", "yarn": "classic" | "berry" | null }`. In standalone mode (no state file) a stage falls back to its own discovery
- `notes` collects non-blocking observations from stages (e.g. `/04-reconcile-work` "ready with conditions")
- Timestamps are ISO 8601 UTC, written by the script
- The script owns `stages`, `current_stage`, `halted`, `completed_at` and `notes`. Skills only ever edit `repos`, `jira` and `pr_template`, with the `Edit` tool

### 5. Why a State File

The stage skills used to be chained by inference, and after a context compaction the model once continued from a summary that said the next step was "pending". That is why every stage skill carries a hard **NO AUTO-CHAINING** stop.

The state file replaces inference with a fact on disk:

- A stage hands off **only** if the file says `mode: chained` and that stage is `in_progress`
- The chain is bounded by `until`; `07` is never reached unless the file says `until: "07"`
- A conversation summary is **never** evidence that the pipeline should continue; only the file is
- `--resume` is trivial: the file knows which stage is unfinished

### 6. Invoke the First Stage

`state init` (or `state resume`) has already set the stage to `in_progress` and made it `current_stage`. Invoke exactly the `next` skill and args it printed via the Skill tool. For reference, the calls are:

| Stage | Skill tool call                                                              |
| ----- | ---------------------------------------------------------------------------- |
| `01`  | skill `01-investigate-task`, args `<JIRA-KEY>`                               |
| `02`  | skill `02-start-task`, args `<JIRA-KEY>` plus `--worktree` unless state has `"worktree": false` |
| `03`  | skill `03-dev-execute`, args `<JIRA-KEY>`                                    |
| `04`  | skill `04-reconcile-work`, args `<JIRA-KEY>`                                 |
| `05`  | skill `05-create-pr`, args `<JIRA-KEY>`                                      |
| `06`  | skill `06-pr-review`, args `<JIRA-KEY>`                                      |
| `07`  | skill `07-complete-task`, args `<JIRA-KEY>`                                  |

From here on, each stage's own **"⛔ Stop or Hand Off"** section advances the state file and invokes the next stage. This skill does not loop; it starts the chain.

### 7. Pipeline Announcements

`state advance` and `state halt` run these for whichever stage finishes or halts the chain. The agent only prints the `message` they return. This section documents what they do.

**Finished** (the stage that equals `until` completed successfully):

1. Sets `current_stage = null` and `completed_at` in the state file
2. Runs `say finished the SDLC pipeline for {SOC-XX}` (replace `{SOC-XX}` with the actual key)
3. Returns a summary table of every stage and its status
4. Returns the next manual step. When `until` is `06`:

   ```
   Pipeline finished before merge. When you are ready:
     /07-complete-task SOC-XX
   ```

   When `until` is `07`: `Pipeline finished. PR merged and SOC-XX is Done.`

5. Leaves the state file in place (it documents the run). It is removed by `--reset`.

**Halted** (a stage failed its gate):

1. Sets `stages[NN].status = "failed"` and `halted = { "stage": "NN", "reason": "<one line>", "at": "<timestamp>" }`
2. Runs `say the SDLC pipeline halted at stage {NN} for {SOC-XX}`
3. Returns the stage, the reason, and:

   ```
   Fix the issue, then continue with:
     /00-run-sdlc SOC-XX --resume
   ```

4. The stage then stops and invokes no further stage.

## Halt Gates per Stage

A stage halts the chain (instead of handing off) when:

| Stage | Halts when                                                                                         | Chained-mode note                                                                                   |
| ----- | -------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------- |
| `01`  | Jira ticket not found; Atlassian MCP unavailable                                                   | The "wait for review" step is skipped; the report is still posted to Jira                           |
| `02`  | Dirty working tree; trunk-protection assertion fails; no "In Progress" transition                  | The complexity recommendation is informational only                                                 |
| `03`  | Ticket not "In Progress"; any test failure that cannot be fixed                                    | —                                                                                                   |
| `04`  | Reconciliation report says **Ready for PR: No**                                                    | "With conditions" continues; the conditions are appended to `notes`                                 |
| `05`  | On a trunk branch; GitHub MCP unavailable; push or PR creation fails                               | —                                                                                                   |
| `06`  | CI checks cannot be made green; a blocker is documented; PR already merged                         | Success = ready-for-merge comment posted (or formal approval). Hands off to `07` only if `until` is `07` |
| `07`  | Any pre-merge check fails; merge fails in any repo                                                 | Only reachable with `--until 07`                                                                    |

## Context Compaction

Pipelines are long and the conversation may be compacted mid-run. Rules for every stage:

- After any compaction, **re-read `.sdlc/<JIRA-KEY>.json` before acting** (`state locate` or `state status` does this)
- If the file says the current stage is `in_progress`, re-verify that stage's own outputs (Jira comment posted, branch exists, PR exists, etc.) before marking it `done`
- Never continue because a summary says a step was "pending"; only the file decides

## Prerequisites

- `.claude/sdlc/sdlc.py` linked into the project (`install.py` does this) and allow-listed as `Bash(python3 -I .claude/sdlc/sdlc.py *)`
- Jira MCP server configured in `.mcp.json`
- GitHub MCP server configured in `.mcp.json` (required when `--until` is `05` or higher)
- Git repository initialized with a remote
- `.sdlc/` and `.worktrees/` listed in `.gitignore` (both are in this repo)

## Error Handling

The skill will:

- Stop with a usage message on invalid or missing arguments
- Refuse to start when a state file already exists and no `--resume`, `--reset`, or `--status` flag was given
- Stop before posting anything to Jira if preflight fails
- Report the exact stage and reason whenever the chain halts
- Leave the state file in place on halt so `--resume` can continue

## Workflow Integration

```
0. /00-run-sdlc SOC-15                  # Runs 1–6 below automatically, then stops
1. /01-investigate-task SOC-15          # Deep investigation
2. /02-start-task SOC-15                # Begin work
3. /03-dev-execute SOC-15               # Implement
4. /04-reconcile-work SOC-15            # Reconciles the work
5. /05-create-pr SOC-15                 # Create PR
6. /06-pr-review SOC-15                 # Review and improve code
7. /07-complete-task SOC-15             # Finish (manual unless --until 07)
```

---

## ⛔ Stop Here

This skill only starts the chain. Once the chain finishes or halts (see "Pipeline Announcements"), stop completely.

- Do NOT invoke `/07-complete-task` unless the state file says `until: "07"`
- Do NOT restart or resume a halted pipeline on your own; the user runs `--resume`
- Do NOT infer from a conversation summary that the pipeline should continue; only the state file decides
