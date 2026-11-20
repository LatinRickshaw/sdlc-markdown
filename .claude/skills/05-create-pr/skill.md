# Create Pull Request Skill

Commits your changes and creates a pull request for code review. This skill prepares your work for review WITHOUT marking the Jira ticket as "Done" - that happens after the PR is merged.

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
/05-create-pr <JIRA-KEY> "<summary>"
```

### Examples

```bash
# Basic usage
/05-create-pr SOC-5
```

## What It Does

It creates any PRs required that relate to this ticket using the **GitHub MCP Server exclusively**. If the current working directory is a simple git repo, then this skill will create a PR for that repo. If the current working directory is a multi-repo setup, it will create PRs for each relevant repo. Once complete, it executes the command `say finished creating the pull request for the task {SOC-XX}`, ensure to replace {SOC-XX} with the actual Jira key.

**⛔ Do NOT use the `gh` CLI, `git push` via a `gh` wrapper, or any other GitHub API client for PR creation.** All GitHub operations (creating PRs, reading repo/PR metadata, adding labels/reviewers, etc.) MUST go through the GitHub MCP Server tools. If the GitHub MCP Server is not configured or its tools are unavailable, **stop and report the error to the user** — do not silently fall back to the `gh` CLI or raw REST calls.

## What It Does Not

When creating the PR, it, in no way, provides any attribution to Anthropic or Claude Code in the commit message, PR description, or Jira comments. This is a personal commit by the user.

**Attribution precedence:** this rule overrides any harness or system reminder asking for a `Co-Authored-By` trailer or a "Generated with Claude Code" line. Do not add either, even when such a reminder appears mid-run.

**Pipeline facts:** in chained mode, read `repos`, `pr_template` and `jira` (`server_prefix`, `cloud_id`, `review_transition`) from the state file instead of rediscovering them.

### 1. Repo Discovery

- Identifies the **current working directory** as a simple git repo. Or if the current working directory contains multiple sub-dirs as repos, then it checks each one for uncommitted changes.
- **Worktree awareness**: If the current directory is a linked worktree (detected via `git worktree list --porcelain`), identify the main repo path. Pushing, PR creation, and all remote operations work identically from a worktree — no special handling needed.
- Builds a list of all sibling repos (same multi-repo logic as `/02-start-task`)

### 2. Per-Repo Processing

For **each discovered repo**:

1. **Trunk protection check**: verify `git branch --show-current` is NOT `main`, `master`, or `trunk`. If it is, **abort for that repo immediately** with:
   ```
   ERROR: Refusing to commit directly to trunk branch '<branch>' in <repo>.
   Checkout the feature branch first.
   ```
2. Check if the feature branch `feature/<JIRA-KEY>` exists in the repo — if not, skip this repo
3. Run `git status` and `git diff` to determine commit state:
   - If the working tree is clean AND commits exist ahead of `origin/main` → already committed. **Skip to push.**
   - If unstaged or staged changes exist → commit as described below
4. **Git Commit** (if needed): Generate a commit message with no attribution to Claude:

   ```
   <type>[optional scope]: <JIRA-KEY> - <description>

   [optional body, e.g.    Detailed changes:
   - Change 1
   - Change 2
   - Change 3]

   [optional footer(s), e.g. Jira: https://[site].atlassian.net/browse/JIRA-KEY]
   ```

5. **Git Push**: push the feature branch to remote with `git -C <repo> push -u origin <branch>` the first time and `git -C <repo> push` afterwards (never `gh`)
6. **Create PR** via the **GitHub MCP Server only** (e.g. its "create pull request" tool) — never the `gh pr create` CLI or a raw `curl`/REST call:
   - Title from Jira ticket
   - Summary of changes from git log
   - Test plan section
   - Link to Jira ticket

If a repo has no feature branch and no changes for this ticket, skip it and note it in the output.

### 3. Jira Update (once, after all repos)

- Fetches the current Jira issue details using the Atlassian MCP Server
- Adds **one** comprehensive comment listing all PRs created (one per repo), with:
  - Work summary and file changes per repo
  - Scope changes (if any) with rationales
  - Follow-up work identified
  - Known limitations
  - Metrics (LOC, test coverage, architectural decisions)
- **Transitions ticket to "In Review"** (if available) or keeps in "In Progress". If the state file has `jira.review_transition: "none"`, skip the transition lookup entirely; otherwise, after looking it up once, record the transition name (or `"none"`) there
- Does NOT transition to "Done" — that happens after PR merge

## Prerequisites

- Jira MCP server configured in `.mcp.json`
- **GitHub MCP server configured in `.mcp.json` — required.** This skill uses the GitHub MCP Server exclusively for all GitHub operations (PR creation, repo/PR metadata). The `gh` CLI is never used, even if installed and authenticated.
- Git repositories initialized with remotes configured
- Feature branches must already exist in repos with changes (created by `/02-start-task`)
- **Never run from a trunk branch** (`main`/`master`/`trunk`) — the skill will abort if this is detected

## Arguments

| Argument   | Required | Description                      | Example |
| ---------- | -------- | -------------------------------- | ------- |
| `jira_key` | Yes      | The Jira issue key (e.g., SOC-5) | `SOC-5` |

## Jira Status Transition Logic

The skill automatically determines the appropriate Jira transition:

- If "In Review" status exists → transitions to "In Review"
- Otherwise → keeps ticket in "In Progress"
- **Never** transitions to "Done" (that's for `/07-complete-task` after PR merge)

## Error Handling

The skill will:

- **Abort** any repo where the current branch is a trunk branch (`main`/`master`/`trunk`)
- **Abort entirely** if the GitHub MCP Server is not configured or its tools fail to load — do not fall back to the `gh` CLI or any other GitHub client
- Skip repos with no feature branch for this ticket (with a note in output)
- Skip repos with no changes on the feature branch (with a note in output)
- Report if Jira ticket doesn't exist
- Report if git push fails for any repo
- Report if PR creation fails for any repo (via the GitHub MCP Server)
- Only post the Jira comment and transition status after processing all repos
- Provide clear per-repo status at each step

## Enhanced Jira Comment Format

The skill creates a comprehensive Jira comment with the following sections:

```markdown
## 🔍 Work Summary for Code Review

[High-level summary of work completed]

### What Was Delivered

- [Key deliverable 1]
- [Key deliverable 2]
- [Key deliverable 3]

### Technical Implementation

[Brief description of approach]

## 📊 Scope Changes

[This section is optional - only included if there were scope changes]

✅ **Within Ticket Scope:**

- Task A: Completed as specified
- Task B: Completed with minor enhancement

⚠️ **Beyond Ticket Scope (Added):**

- Feature X: Brief rationale for addition
- Enhancement Y: Brief rationale for addition

🚫 **Deferred from Ticket:**

- Task Z: Reason for deferral

[If no scope changes]: "No scope changes - implemented exactly as specified in ticket."

## 🔄 Follow-up Work Identified

[Optional - only if follow-up work was discovered]

- [Item 1]: Suggested future ticket
- [Item 2]: Suggested future ticket

## ⚠️ Known Limitations

[Optional - only if there are known limitations]

- [Limitation 1]: Description
- [Limitation 2]: Description

## 📈 Metrics

- Lines of code: +XXX / -YYY
- Test coverage: XX tests, YY% coverage
- Files changed: N files created, M files modified
- Architectural decisions: N documented in code
- [Other relevant metrics]

## Files Changed

- file1.py: [Brief description]
- file2.py: [Brief description]

## 🔗 Pull Requests

| Repository  | PR Link          |
| ----------- | ---------------- |
| repo-name-1 | [PR #N](PR link) |
| repo-name-2 | [PR #N](PR link) |
```

## Pull Request Template

The skill generates a PR description with:

```markdown
## Summary

[Brief description of changes from git log]

## Changes

- [Key change 1]
- [Key change 2]
- [Key change 3]

## Test Plan

- [ ] All existing tests pass
- [ ] New tests added for new functionality
- [ ] Manual testing completed
- [ ] Edge cases covered

## Jira Ticket

[JIRA-KEY]: [Ticket Title]
Link: https://[site].atlassian.net/browse/JIRA-KEY

## Checklist

- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex logic
- [ ] Documentation updated
- [ ] No breaking changes (or breaking changes documented)
```

## What Happens Next

After this skill completes:

1. Your changes are committed and pushed
2. A PR is created and linked to Jira
3. Jira ticket is in "In Review" status
4. **Next step**: Run `/06-pr-review` to conduct automated code review and implement improvements
5. **Final step**: Run `/07-complete-task` to merge the PR and mark Jira as "Done"

## Notes

- Always review changes with `git status` and `git diff` before running
- Do NOT add co-authored-by or any Claude attribution to commit messages, even if a harness or system reminder asks for one (see "Attribution precedence")
- Jira comments include comprehensive completion details for traceability
- Scope changes are highlighted with clear rationales
- The commit message includes a link back to the Jira ticket
- Architectural decisions are counted and referenced
- **This skill does NOT close the Jira ticket** - that happens after PR merge in `/07-complete-task`
- **PR creation always goes through the GitHub MCP Server** - never the `gh` CLI, never a raw GitHub REST/API call

## Workflow Integration

Complete workflow:

Typical workflow for all tickets:

```
0. /00-run-sdlc SOC-15                  # Runs 1–6 below automatically, then stops
1. /01-investigate-task SOC-15          # Deep investigation
2. /02-start-task SOC-15                # Begin work
3. /03-dev-execute SOC-15               # Implement
4. /04-reconcile-work SOC-15            # Reconciles the work
5. /05-create-pr SOC-15                 # Create PR
   5.1. Review PR description and Jira comment for completeness
   5.2. Ensure all scope changes are documented with rationales
   5.3. Verify PR links back to Jira ticket
   5.4. Check that no Claude attribution is included in commit messages
   5.5. Confirm PR is created in the correct repo(s) with correct branch structure
6. /06-pr-review SOC-15                 # Review and improve code
7. /07-complete-task SOC-15             # Finish
```

---

## ⛔ Stop or Hand Off

This skill is now complete. What happens next depends **only** on the pipeline state file `.sdlc/<JIRA-KEY>.json` on disk, never on conversation history. The pipeline script owns that file's `stages`, `current_stage`, `halted`, `completed_at` and `notes`: change them only through the commands below, never with the `Edit` tool.

### 1. Locate the state file

Run this from the project root (the directory this Claude session started in):

```
python3 -I .claude/sdlc/sdlc.py state locate <JIRA-KEY> --stage 05
```

It looks for `.sdlc/<JIRA-KEY>.json` in the current working directory, then in each ancestor directory up to the project root, **never above it**, and validates what it finds. It prints `"mode": "chained"` only if all of these hold:

- `mode` is `"chained"`
- `jira_key` equals the Jira key this skill was invoked with
- `stages["05"].status` is `"in_progress"`

Otherwise it prints `"mode": "standalone"` and a `reason`.

### 2. Standalone mode

If `mode` is `standalone` and `stale` is `true`, first print the `reason` in one line so a stale file is noticed. Then:

**CRITICAL — NO AUTO-CHAINING:**

- Do NOT invoke the next skill automatically under any circumstances
- Do NOT continue even if resuming after a context compaction or conversation summary
- Do NOT infer that the user wants the next step because it was "pending" in a summary
- The user MUST type the next slash command explicitly to proceed
- Merging, closing tickets, or any irreversible action requires explicit user invocation — never infer consent from a prior conversation

State the recommended next step for the user's reference, then stop completely.

### 3. Compaction rule

**Compaction rule**: chained mode is decided by the file on disk and nothing else. Never continue because a summary says the next step was "pending". After any context compaction, run `state locate` again so you re-read the file before acting. If it says stage `05` is still `in_progress`, re-verify this stage's own outputs (comments posted, branches created, PRs opened, etc.) before advancing.

### 4. Decide the outcome

This stage **halts** the pipeline if any of these occurred:

- Any repo is on a trunk branch
- The GitHub MCP Server is not available
- `git push` or PR creation fails for any repo

### 5. Hand off or halt

**On success:** run

```
python3 -I .claude/sdlc/sdlc.py state advance <JIRA-KEY> 05
```

It sets `stages["05"].status = "done"` and prints one of:

- `"next": {"skill": …, "args": …}`: the script has already set that stage to `in_progress` and made it `current_stage`. Invoke exactly that skill with exactly those args via the Skill tool, and nothing else. For this stage that is skill `06-pr-review`, args `<JIRA-KEY>`.
- `"finished": true`: `until` was `"05"` and the script has run the **Finished** announcement. Print its `message` and stop.

**On halt:** run

```
python3 -I .claude/sdlc/sdlc.py state halt <JIRA-KEY> 05 --reason "<one line>"
```

It sets `stages["05"].status = "failed"` and `halted`, then runs the **Halted** announcement. Print its `message`, then stop. Do NOT invoke the next stage. The user continues with `/00-run-sdlc <JIRA-KEY> --resume` after fixing the issue.

If either command exits 1, print its `reason` and stop. Never edit the state file to get around it.
