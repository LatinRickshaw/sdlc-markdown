# Start Task Skill

**IMPORTANT: This skill ONLY handles task setup. It does NOT implement the task or write code.**

Automates the workflow for **preparing to begin** a development task:

1. Checks git status to ensure working directory is clean
2. **Discovers all sub git repositories** in the current working directory
3. Creates the feature branch in the repos that changes will be made in. Does not create branches in repos that are out of scope.
4. Fetches the Jira ticket details using the Atlassian MCP server
5. Transitions the Jira ticket to "In Progress" using the Atlassian MCP Server
6. Adds a comment to the Jira ticket indicating work has started, listing all repos in scope, using the Atlassian MCP Server
7. Once complete, it executes the command `say finished starting the task {SOC-XX}`, ensure to replace {SOC-XX} with the actual Jira key.

**After this skill completes, the user should use `/03-dev-execute` to actually implement the task.**

## Shell & Tool Conventions

These rules keep the skill runnable without permission prompts. Claude Code auto-approves only commands it can prove are read-only, and the project ships a PreToolUse hook that extends that proof; both are defeated by the shapes below.

- Prefer the `Read`, `Grep` and `Glob` tools over Bash `cat`, `grep`, `find` and `sed -n` **if they are listed** in this session; they never prompt inside the project. If `Glob`/`Grep` are not available, fall back to `ls -d */.git` (repo discovery), `ls <dir>`, `grep -n <pattern> <file>` and `git -C <repo> grep -n <pattern>` via Bash; all are auto-approved. Never call a tool that is not listed.
- **Never `cd <dir> && git …`.** Running git after a `cd` into another directory always prompts. Use `git -C <absolute-repo-path> <subcommand>`, one git operation per Bash call.
- No `for`/`while` loops over repos. Run one command per repo per Bash call; parallel calls are fine.
- JSON: `jq` only. Never `python3 -c` or `node -e`; inline scripts are arbitrary code and always prompt.
- No redirects to files except `2>/dev/null`. No `$(…)`, backticks, heredocs, `xargs` with flags, or `find -exec`/`-delete`.
- Files this skill creates (state file, reports) are written with the `Write`/`Edit` tools, never `cat <<EOF >` or `echo >`.
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
/02-start-task <JIRA-KEY> [--worktree]
```

### Examples

```bash
# Basic usage (in-place branch checkout)
/02-start-task SOC-5

# Worktree mode (creates isolated sibling directory)
/02-start-task SOC-5 --worktree
```

## What It Does

### 1. Git Status Check

- Runs `git status` to verify the current working directory is clean. If the working directory contains multiple sub-dirs as repos, then it checks each one for uncommitted changes.
- If there are uncommitted changes, warns the user and stops
- Ensures you're starting from a clean slate

### 2. Repo Discovery

- Identifies the **current working directory**
- **In chained mode, read `repos` from the state file first** and skip the scan if it is filled. If it is empty (the run started at `02`), fill it as `/01-investigate-task` step 2b describes. In worktree mode, replace each in-scope `repos[].path` with its worktree path once the worktree exists, so later stages run commands there
- Otherwise scans all immediate subdirectories of the **current working directory** for those containing a `.git` folder (use the `Glob` tool with `*/.git` if it is listed, else `ls -d */.git`; no `ls | xargs sh -c` loops)
- Builds a list of all sub repos (including the current repo)
- Reports which repos were discovered

### 3. Branch Setup (per repo)

For **each discovered repo**:

1. Check git status with `git -C <absolute-repo-path> status --short` (one Bash call per repo, never `cd <repo> && git …`) — if the repo has uncommitted changes, **warn the user and STOP!!!**
2. Identify the trunk branch (`main`, `master`, or `trunk` — whichever exists)
3. Checkout the trunk branch
4. Pull latest changes from remote
5. Only create and checkout the feature branch: `feature/<JIRA-KEY>-<description>` where applicable. If changes are not going to be made in a repo, do NOT create a branch in that repo.
6. **Trunk protection assertion**: after checkout, verify `git branch --show-current` returns the feature branch name — if it still shows the trunk branch, abort immediately with:
   ```
   ERROR: Failed to switch off trunk branch '<branch>' in <repo>.
   Feature branch creation may have failed. Do not proceed.
   ```

> Example feature branch: `feature/SOC-4-platform-templates-optimization`

### 3b. Worktree Mode (when `--worktree` flag is provided)

Instead of checking out the feature branch in-place (Step 3), worktree mode creates an isolated sibling directory for the ticket. This allows multiple tickets to be worked on simultaneously in separate Claude Code sessions.

**For single-repo setups:**

1. From the repo root, create a worktree in a `.worktrees/` subdirectory:
   ```bash
   git worktree add .worktrees/<JIRA-KEY> -b feature/<JIRA-KEY>-<description>
   ```
   Example: `git worktree add .worktrees/SOC-15 -b feature/SOC-15-platform-templates`
2. Change working directory to the new worktree path
3. Verify branch with `git branch --show-current`

**For multi-repo setups:**

1. For each in-scope sub-repo, create a worktree inside its own `.worktrees/` subdirectory:
   ```bash
   cd <sub-repo>
   git worktree add .worktrees/<JIRA-KEY> -b feature/<JIRA-KEY>-<description>
   ```
2. Verify all branches in all sub-repo worktrees

**Worktree detection & reuse:**

- Before creating a new worktree, run `git worktree list` to check if one already exists for this ticket's branch
- If a worktree already exists for `feature/<JIRA-KEY>`, switch to it instead of creating a new one
- Report the worktree path to the user so they can open additional Claude Code sessions there

**Important worktree notes:**

- Git prevents checking out the same branch in two worktrees — this is a safety feature that prevents conflicts
- The `.worktrees/` directory must be added to `.gitignore` to prevent tracking worktree contents
- The worktree shares `.git` history with the main repo, so commits are visible across all worktrees
- All standard git operations (commit, push, pull, status, diff) work identically inside a worktree
- The worktree is cleaned up by `/07-complete-task` after the PR is merged

**Trunk protection assertion (worktree mode):** After worktree creation, verify `git branch --show-current` returns the feature branch name in the worktree directory — if it shows the trunk branch, abort immediately.

### 4. Fetch Jira Ticket using Atlassian MCP Server

- Retrieves the Jira issue details using the Atlassian MCP Server (in chained mode, the server named by `jira.server_prefix` in the state file, with `jira.cloud_id`; no `getAccessibleAtlassianResources` lookup)
- Displays the ticket summary and current status
- Confirms the ticket exists before proceeding

### 5. Transition to In Progress using the Atlassian MCP Server

- Fetches available transitions for the ticket using the Atlassian MCP Server
- Looks for "In Progress" transition using the Atlassian MCP Server
- Transitions the ticket from current status (e.g., "To Do") to "In Progress" using the Atlassian MCP Server
- Handles custom workflow transitions automatically

### 6. Add Jira Comment using the Atlassian MCP Server

- Adds a comment to the Jira ticket: "Started work on this task" using the Atlassian MCP Server
- Lists all repos where feature branches were successfully created
- Provides traceability of when work began
- Visible to the team in Jira

### 7. Analyze Complexity & Recommend Investigation

After transitioning the ticket to "In Progress", analyze ticket content for complexity indicators:

**Complexity Keywords Detection:**

Check ticket summary and description for these keywords:

- **Deprecation/Migration**: "deprecated", "migration", "upgrade", "breaking change"
- **Architecture**: "architecture", "refactor", "redesign", "restructure"
- **Performance/Security**: "performance", "security", "scalability", "optimization"
- **Unknown/Research**: "investigate", "research", "unknown", "unclear", "complex"
- **Integration**: "integrate", "external API", "third-party", "service"

**Recommendation Logic:**

If complexity keywords are detected:

1. Display detected keywords to user
2. Show non-blocking recommendation to run `/01-investigate-task`
3. Explain what investigation will provide
4. Clarify that investigation is optional - user can skip if requirements are clear

**When NOT to Suggest:**

Do NOT suggest investigation for tickets with:

- Bug fixes with known solution
- Simple UI changes
- Documentation updates
- Configuration changes
- "simple" or "trivial" labels

**Output Format:**

```
⚠️  COMPLEXITY INDICATORS DETECTED

Keywords found: deprecated, migration, API

RECOMMENDATION:
This task may benefit from technical investigation.

Consider running: /01-investigate-task SOC-XX

Investigation will:
  • Analyze codebase for existing patterns
  • Identify deprecated dependencies
  • Document architectural decisions needed
  • Assess complexity and risks
  • Post findings to Jira for team review

You can skip if requirements are already clear.
```

## What It Does NOT Do

**CRITICAL: This skill stops after setup and does NOT:**

- This skill does not Read or analyze the codebase
- This skill does not Write any code or implementation
- This skill does not Create or modify files (except git operations)
- This skill does not Run tests
- This skill does not Make commits
- This skill does not Execute the task requirements

**The actual implementation work should be done with `/03-dev-execute` after this skill completes.**

## Prerequisites

- Jira MCP server configured in `.mcp.json`
- Git repository initialized
- Git remote configured (optional, for sync check)
- Working directory should be clean (no uncommitted changes)

## Arguments

| Argument     | Required | Description                                                                 | Example |
| ------------ | -------- | --------------------------------------------------------------------------- | ------- |
| `jira_key`   | Yes      | The Jira issue key to start working on                                      | `SOC-5` |
| `--worktree` | No       | Creates an isolated sibling directory worktree instead of in-place checkout  | —       |

## Transition Logic

The skill automatically determines the appropriate Jira transition:

- Looks for transition named "In Progress" (case-insensitive) using the Atlassian MCP Server
- If not found, looks for similar transitions (e.g., "Start Progress", "Begin") using the Atlassian MCP Server
- Reports an error if no suitable transition is found
- Shows current status and available transitions for debugging

## Error Handling

The skill will:

- Stop if the current working directory, or any sub-dir repos has uncommitted changes
- Abort immediately if branch creation leaves any repo on a trunk branch
- Stop if the Atlassian MCP Server stops working
- Report if Jira ticket doesn't exist
- Report if "In Progress" transition is not available
- Provide clear error messages at each step

## Notes

- Use `git status` to check your working directory before running
- The skill ensures you don't accidentally mix work from multiple tickets
- **Never commits directly to trunk** — feature branches are always created first
- Jira comments provide audit trail of when work started and which repos are in scope
- **Worktree mode** (`--worktree`): Creates an isolated `.worktrees/<JIRA-KEY>` subdirectory, allowing multiple tickets to be worked on in parallel across separate Claude Code sessions. All subsequent skills (03–07) work identically in a worktree. Cleanup happens automatically in `/07-complete-task`.

## Workflow Integration

Typical workflow for all tickets:

```
0. /00-run-sdlc SOC-15                  # Runs 1–6 below automatically, then stops
1. /01-investigate-task SOC-15          # Deep investigation
2. /02-start-task SOC-15                # Begin work
   2.1. Transition ticket to "In Progress"
   2.2. Create feature branches in all repos
   2.3. Comment on Jira with repos in scope
3. /03-dev-execute SOC-15               # Implement
4. /04-reconcile-work SOC-15            # Reconciles the work
5. /05-create-pr SOC-15                 # Create PR
6. /06-pr-review SOC-15                 # Review and improve code
7. /07-complete-task SOC-15             # Finish
```

### Example: Simple Task (No Investigation)

```bash
/02-start-task SOC-22
```

### Example: Complex Task (Investigation Recommended)

```bash
/02-start-task SOC-14
# Output: ⚠️  COMPLEXITY INDICATORS DETECTED
#         Keywords found: deprecated, migration
#         Consider running: /01-investigate-task SOC-14
```

---

## ⛔ Stop or Hand Off

This skill is now complete. What happens next depends **only** on a pipeline state file on disk, never on conversation history.

### 1. Locate the state file

Look for `.sdlc/<JIRA-KEY>.json` in the current working directory, then in each ancestor directory up to the project root (the directory this Claude session started in), **never above it**. This covers worktrees under `.worktrees/` and multi-repo parent directories. Use the `Read` tool (plus `Glob` if it is listed; otherwise `ls .sdlc/` run from each directory inside the project): looking above the project root prompts and can pick up an unrelated pipeline's file. Use the first file found.

### 2. Standalone mode (no state file, or the file fails validation)

If no file is found, or the file fails any check in step 3, you are in standalone mode. If a file was found but failed validation, first print one line naming the file and the failed check (wrong `jira_key`, `mode` not `chained`, or stage `02` not `in_progress`) so a stale file is noticed. Then:

**CRITICAL — NO AUTO-CHAINING:**

- Do NOT invoke the next skill automatically under any circumstances
- Do NOT continue even if resuming after a context compaction or conversation summary
- Do NOT infer that the user wants the next step because it was "pending" in a summary
- The user MUST type the next slash command explicitly to proceed
- Merging, closing tickets, or any irreversible action requires explicit user invocation — never infer consent from a prior conversation

State the recommended next step for the user's reference, then stop completely.

### 3. Chained mode validation

Chained mode applies only if **all** of the following hold in the file:

- `mode` is `"chained"`
- `jira_key` equals the Jira key this skill was invoked with
- `stages["02"].status` is `"in_progress"`

**Compaction rule**: chained mode is decided by the file on disk and nothing else. Never continue because a summary says the next step was "pending". After any context compaction, re-read the file before acting. If the file says stage `02` is still `in_progress`, re-verify this stage's own outputs (comments posted, branches created, PRs opened, etc.) before marking it done.

### 4. Decide the outcome

This stage **halts** the pipeline if any of these occurred:

- Any repo has uncommitted changes
- The trunk-protection assertion fails in any repo
- No "In Progress" (or equivalent) transition is available

> In chained mode the complexity recommendation is informational only. Do not wait for the user to decide whether to investigate.

### 5. Hand off or halt

Update the state file with the `Edit` tool (never a shell redirect) and take timestamps from `date -u +%Y-%m-%dT%H:%M:%SZ`.

**On success:**

1. Set `stages["02"].status = "done"` and `stages["02"].finished_at` in the state file.
2. Then:
   - If `until` equals `"02"`, run the **Finished** announcement from `/00-run-sdlc` ("Pipeline Announcements") and stop.
   - Otherwise, set `stages["03"].status = "in_progress"`, `stages["03"].started_at`, and `current_stage = "03"`, then invoke the next stage via the Skill tool: skill `03-dev-execute`, args `<JIRA-KEY>`.

**On halt:**

1. Set `stages["02"].status = "failed"` and `halted = { "stage": "02", "reason": "<one line>", "at": "<timestamp>" }`.
2. Run the **Halted** announcement from `/00-run-sdlc` ("Pipeline Announcements").
3. Stop. Do NOT invoke the next stage. The user continues with `/00-run-sdlc <JIRA-KEY> --resume` after fixing the issue.
