# Run SDLC Pipeline Skill

Runs the SDLC skills `01` → `07` as one automated chain for a Jira ticket. By default it runs investigation through PR review (`01` → `06`) and **stops before merge**. Merging and closing the ticket (`07`) only happens when you explicitly pass `--until 07`.

Chained mode is recorded in a **state file on disk** (`.sdlc/<JIRA-KEY>.json`). Each stage skill reads that file at its end to decide whether to hand off to the next stage. Without the file, every skill behaves exactly as it does today: it stops and waits for you.

## Shell & Tool Conventions

These rules keep the skill runnable without permission prompts. Claude Code auto-approves only commands it can prove are read-only, and the project ships a PreToolUse hook that extends that proof; both are defeated by the shapes below.

- Prefer the `Read`, `Grep` and `Glob` tools over Bash `cat`, `grep`, `find` and `sed -n`; they never prompt inside the project.
- **Never `cd <dir> && git …`.** Running git after a `cd` into another directory always prompts. Use `git -C <absolute-repo-path> <subcommand>`, one git operation per Bash call.
- No `for`/`while` loops over repos. Run one command per repo per Bash call; parallel calls are fine.
- JSON: `jq` only. Never `python3 -c` or `node -e`; inline scripts are arbitrary code and always prompt.
- No redirects to files except `2>/dev/null`. No `$(…)`, backticks, heredocs, `xargs` with flags, or `find -exec`/`-delete`.
- Files this skill creates (state file, reports) are written with the `Write`/`Edit` tools, never `cat <<EOF >` or `echo >`.
- Temporary reports go in the session scratchpad directory, never in a repo.
- Security advisories and registry metadata via the `WebFetch` tool, never `curl`.
- Keep each command single-line with simple quoting; one job per call.

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

### 1. Parse & Validate Arguments

- Extract `<JIRA-KEY>` (required) and flags
- `--from` and `--until` must be in `01`–`07` and `from ≤ until`; otherwise stop with a clear error
- Worktree mode is the **default**: `/02-start-task` is invoked with `--worktree` unless `--no-worktree` was given. The worktree is created under `.worktrees/<JIRA-KEY>` and removed by `/07-complete-task`.
- If `--until 07`: print this warning, then continue (the user asked for it on the command line):

  ```
  ⚠️  --until 07 will MERGE the pull request(s) and transition the Jira ticket to "Done" without pausing.
  ```

### 2. Handle an Existing State File

Look for `.sdlc/<JIRA-KEY>.json` in the **current working directory** (the pipeline root).

| State file exists? | Flag       | Action                                                                                               |
| ------------------ | ---------- | ---------------------------------------------------------------------------------------------------- |
| No                 | any        | Create a new pipeline (step 3 onward)                                                                |
| Yes                | `--status` | Read the file with the `Read` tool and print its contents plus a one-line summary (current stage, halted reason if any). **Stop.** |
| Yes                | `--resume` | Validate `jira_key` matches. Find the first stage (in `from`→`until` order) whose status is not `done` or `skipped`. Set it to `in_progress`, clear `halted`, and invoke it (step 6). |
| Yes                | `--reset`  | Delete the file with exactly `rm .sdlc/<JIRA-KEY>.json` from the pipeline root (that relative form is pre-approved), then create a new pipeline (step 3 onward) |
| Yes                | none       | **Refuse.** Print the current stage and status and the three options above. Do not run anything.    |

### 3. Preflight (fail fast, before anything is posted to Jira)

1. **Jira reachable**: fetch the ticket via the Atlassian MCP Server. Stop if the ticket does not exist or the server is unavailable.
2. **GitHub MCP available** (only if `until ≥ 05`): confirm the GitHub MCP Server tools are loaded. `/05-create-pr` refuses to fall back to the `gh` CLI, so stop now rather than after implementation.
3. **Clean working tree** (only if `from ≤ 02`): discover repos with the `Glob` tool (`*/.git` plus the current directory, same discovery as `/02-start-task`), then run `git -C <absolute-repo-path> status --short` once per repo, each in its own Bash call (no `cd`, no loops). Stop if any repo has uncommitted changes.

### 4. Create the State File

Write `.sdlc/<JIRA-KEY>.json` in the current working directory with the `Write` tool (it creates `.sdlc/` as needed; no `mkdir`, no shell redirect):

```json
{
  "jira_key": "SOC-15",
  "mode": "chained",
  "from": "01",
  "until": "06",
  "worktree": true,
  "pipeline_root": "/absolute/path/to/cwd",
  "started_at": "2026-11-16T10:00:00Z",
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
- `halted` is `null` or `{ "stage": "04", "reason": "…", "at": "…" }`
- `notes` collects non-blocking observations from stages (e.g. `/04-reconcile-work` "ready with conditions")
- Timestamps are ISO 8601 UTC, taken from `date -u +%Y-%m-%dT%H:%M:%SZ`

### 5. Why a State File

The stage skills used to be chained by inference, and after a context compaction the model once continued from a summary that said the next step was "pending". That is why every stage skill carries a hard **NO AUTO-CHAINING** stop.

The state file replaces inference with a fact on disk:

- A stage hands off **only** if the file says `mode: chained` and that stage is `in_progress`
- The chain is bounded by `until`; `07` is never reached unless the file says `until: "07"`
- A conversation summary is **never** evidence that the pipeline should continue; only the file is
- `--resume` is trivial: the file knows which stage is unfinished

### 6. Invoke the First Stage

Set `stages[from].status = "in_progress"` and `current_stage = from`, then invoke the stage via the Skill tool:

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

These are run by whichever stage finishes or halts the chain (the stage skills reference this section).

**Finished** (the stage that equals `until` completed successfully):

1. Set `current_stage = null` and `completed_at` in the state file
2. Run `say finished the SDLC pipeline for {SOC-XX}` (replace `{SOC-XX}` with the actual key)
3. Print a summary table of every stage and its status
4. Print the next manual step. When `until` is `06`:

   ```
   Pipeline finished before merge. When you are ready:
     /07-complete-task SOC-XX
   ```

   When `until` is `07`: `Pipeline finished. PR merged and SOC-XX is Done.`

5. Leave the state file in place (it documents the run). It is removed by `--reset` or by hand.

**Halted** (a stage failed its gate):

1. Set `stages[NN].status = "failed"` and `halted = { "stage": "NN", "reason": "<one line>", "at": "<timestamp>" }`
2. Run `say the SDLC pipeline halted at stage {NN} for {SOC-XX}`
3. Print the stage, the reason, and:

   ```
   Fix the issue, then continue with:
     /00-run-sdlc SOC-XX --resume
   ```

4. Stop. Do not invoke any further stage.

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

- After any compaction, **re-read `.sdlc/<JIRA-KEY>.json` before acting**
- If the file says the current stage is `in_progress`, re-verify that stage's own outputs (Jira comment posted, branch exists, PR exists, etc.) before marking it `done`
- Never continue because a summary says a step was "pending"; only the file decides

## Prerequisites

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
