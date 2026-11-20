# Complete Task Skill

Merges an approved pull request and marks the Jira ticket as "Done". This is the final step in the development workflow, executed after code review is complete.

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
/07-complete-task [JIRA-KEY] [--prune-branches]
```

### Examples

```bash
# Complete with explicit Jira key
/07-complete-task SOC-15

# Also delete the local feature branch(es) after merge (asks for approval: `branch -D` is an ask rule)
/07-complete-task SOC-15 --prune-branches
```

## What It Does

Marges any open PRs relating to this ticket. Transitions the relevant ticket in JIRA. Once complete, it executes the command `say finished completing the task {SOC-XX}`, ensure to replace {SOC-XX} with the actual Jira key.

### 1. Read State, Ask Pending Questions, Discover PRs

- **Read the state file first** if one exists (`.sdlc/<JIRA-KEY>.json`, located as described in "Locate the state file" below). Do this even in standalone mode, for example when the user runs `/07` by hand after a halt at `06`. Take `repos`, `jira.server_prefix` and `jira.cloud_id` from it instead of rediscovering them.
- **Override question, asked up front:** if `halted.stage` is `"06"` and `halted.advisory_diff` is present, `/06-pr-review` stopped on a pre-existing audit failure. Ask the user once, with `AskUserQuestion`, in this step. Start the CI re-check (step 2) in the same turn so the two overlap.
  - Show the per-repo `new` / `fixed` / `unchanged` advisory IDs in the question.
  - Options: **Merge anyway** (the audit failure is pre-existing and not caused by this PR) or **Stop** (do not merge).
  - On **Stop**, end the skill without merging or transitioning Jira.
  - On **Merge anyway**, the failing audit check is accepted for this run only, as long as the advisory set has not grown (re-check: no `new` IDs). Every other check must still pass.
- Without a state file: identify the **current working directory** and scan all sub repos for git repositories (same discovery logic as `/02-start-task`).
- For each repo, use `list_pull_requests` via GitHub MCP (filtered by `feature/<JIRA-KEY>` head branch) to find open PRs.
- Compile the full list of PRs to merge across all repos.

### 2. PR Verification and Sibling Drift (per repo)

For each discovered PR:

1. **Always fetch main first**: `git -C <repo> fetch origin main`. A sibling ticket may have landed on `main` since `/06-pr-review` ran.
2. Fetch the PR with `pull_request_read` (method `get`) via GitHub MCP.
3. Verify the PR is approved by required reviewers, OR confirm a ✅ ready-for-merge review summary comment was posted by `/06-pr-review` (covers solo repos where self-approval is blocked by GitHub). A ⛔ pre-existing-audit comment counts only if the user chose **Merge anyway** in step 1.
4. **Sibling drift**: the branch has drifted if any of these hold:
   - `mergeable_state` is `dirty` or `unknown`
   - `git -C <repo> merge-base --is-ancestor origin/main HEAD` fails, meaning main has moved past the PR base

   For `unknown`, re-fetch the PR once after a background `sleep 90` first, because GitHub may still be computing it. If the branch has drifted:
   1. `git -C <repo> merge origin/main --no-edit` (resolve any conflicts; for a lockfile conflict, take main's lockfile and re-run install)
   2. install with the lockfile frozen, then build and test, all using the **Command shapes** above (`yarn --cwd <repo> install --frozen-lockfile` for classic, `cd <repo> && corepack yarn install --immutable` for berry)
   3. `git -C <repo> push`
   4. Wait for CI with the **CI waiting procedure** (the same procedure as `/06-pr-review`: `pull_request_read` method `get_check_runs` after a background `sleep 90`, never `gh`). If a question is still pending, ask it while CI runs.
5. Fetch all check runs with `pull_request_read` method `get_check_runs` and confirm they all pass. The only exception is an audit check the user accepted in step 1. An empty list with `mergeable_state: dirty` means the PR is conflicted, so go back to step 4.
6. Confirm no merge conflicts exist and the PR is not a draft.

### 3. Merge Pull Requests (per repo)

For each verified PR:

- Merges using the appropriate strategy via GitHub MCP:
  - **Squash merge** (default): Combines all commits into one clean commit
  - **Merge commit**: Preserves all commits (if repo configured)
  - **Rebase**: Rebases and fast-forwards (if repo configured)
- Confirms merge was successful before proceeding to the next repo
- Repos are merged **independently**: one repo's drift or CI wait does not block verifying and merging the others
- If any merge fails: reports which repos succeeded and which failed, and **does not transition Jira to "Done"** until all repos are merged

### 4. Jira Finalization (once — after all repos merged)

- Fetches current Jira issue details using Atlassian MCP (the server in `jira.server_prefix` with `jira.cloud_id` when a state file exists)
- Adds final comment to Jira listing all merged PRs:
  - PR merged confirmation per repo
  - Link to each merged PR
  - Final commit SHA per repo
  - Deployment status (if available)
- **Transitions Jira ticket to "Done"** — only after all repos are successfully merged
- Records completion timestamp

### 5. Cleanup (per repo)

- Deletes the remote feature branch: `git -C <repo> push origin --delete <branch>` (skip if GitHub already deleted it on merge)
- Prunes stale remote refs: `git -C <repo> fetch --prune`
- Switches back to the trunk branch in each repo (non-worktree mode) and syncs with remote
- **Local branch deletion is opt-in.** Only with `--prune-branches`, run `git -C <repo> branch -D <branch>` from the main checkout, after the worktree is removed (step 6). `branch -D` is a deliberate `ask` rule, so the user approves it. Without the flag, leave the local branch in place: once the worktree is gone, a squash-merged local branch is harmless.

### 6. Worktree Cleanup (Automatic when in a worktree)

After successful merge, detect if the current working directory is a git worktree (not the main working tree):

```bash
# Check if current directory is a linked worktree
git worktree list --porcelain
```

**If currently in a worktree:**

1. Record the current worktree path and identify the main repo path from `git worktree list --porcelain`
2. Change working directory to the main repo or the pipeline root first, so the shell's cwd is not inside the directory being removed
3. Remove the worktree:
   ```bash
   git -C <main-repo> worktree remove .worktrees/<JIRA-KEY>
   ```
4. For multi-repo setups: each sub-repo cleans up its own `.worktrees/<JIRA-KEY>`. If the `.worktrees/` directory is empty after removal, delete it as well.
5. Run `git -C <main-repo> worktree prune` to clean up any stale worktree references
6. Only with `--prune-branches`: `git -C <main-repo> branch -D <branch>` (see Cleanup)
7. Inform the user that the worktree has been cleaned up and they are now back in the main repo

**If NOT in a worktree:** No change to current behavior — skip this step entirely.

**If worktree removal fails** (e.g. uncommitted changes in worktree):
- Report the error clearly
- Do NOT force-remove — the user may have uncommitted work
- Suggest manual cleanup: `git worktree remove --force <path>` if they are sure

## Prerequisites

- GitHub MCP server configured in [.mcp.json](../.mcp.json)
- Jira MCP server configured in [.mcp.json](../.mcp.json)
- PR must be approved
- All status checks must pass
- No merge conflicts
- User must have merge permissions

## Arguments

| Argument   | Required | Description                         | Example  |
| ---------- | -------- | ----------------------------------- | -------- |
| `jira_key` | Yes      | Jira key (auto-detected if omitted) | `SOC-15` |
| `--prune-branches` | No | Also delete the local feature branch after merge (prompts: `branch -D` is an ask rule). Off by default | — |

## Merge Strategy

The skill uses the repository's configured merge strategy:

### Squash Merge (Default)

- Combines all PR commits into single commit
- Clean, linear history
- Best for most projects
- Commit message from PR title and description

### Merge Commit

- Preserves all individual commits
- Shows full development history
- Useful for complex features
- Creates merge commit linking branches

### Rebase

- Replays commits on top of base branch
- Linear history without merge commits
- Requires clean, well-structured commits
- May require force push if conflicts

## Pre-Merge Checks

The skill verifies these conditions before merging:

1. ✅ PR is approved by required reviewers, OR a ✅ ready-for-merge comment was posted by `/06-pr-review` (soft check — not a hard blocker for solo repos)
2. ✅ All required status checks pass (CI/CD, tests, linting)
3. ✅ No merge conflicts with base branch
4. ✅ PR is not in draft state
5. ✅ Branch is up-to-date with base (or can be updated)

If any check fails, the skill will:

- Report which check failed
- Provide guidance on how to resolve
- Not merge the PR
- Not transition Jira ticket

## Jira Final Comment Format

```markdown
## ✅ Task Completed

Pull request has been merged and deployed.

### Merge Details

- **PR**: #42 - [PR Title]
- **Merged**: 2024-01-15 14:30 UTC
- **Commit**: abc123def456
- **Strategy**: Squash merge

### Deployment Status

- **Environment**: Production
- **Status**: ✅ Deployed successfully
- **Link**: [Deployment URL]

[Or if not yet deployed]

- **Status**: ⏳ Pending deployment
- **Next**: Will deploy in next release

### Branch Cleanup

- ✅ Remote branch deleted
- ✅ Worktree removed
- ✅ Local branch deleted (only with `--prune-branches`)

Task is now complete and changes are live.
```

## Error Handling

The skill handles common scenarios:

### PR Not Approved

```
❌ Cannot merge: PR requires 1 more approval
Action: Request review from team members
```

### Status Checks Failing

```
❌ Cannot merge: 2 checks failing
- ❌ CI/CD Build (test failures in test_api.py)
- ❌ Code Coverage (dropped below 80%)
Action: Fix failing tests and push changes
```

### Merge Conflicts

```
❌ Cannot merge: Conflicts with main branch
Files in conflict:
- src/api/routes.py
- tests/test_routes.py
Action: Resolve conflicts locally and push
```

### Permission Denied

```
❌ Cannot merge: Insufficient permissions
Action: Request merge from repo admin or team lead
```

## What Happens Next

After this skill completes:

1. ✅ PR is merged to main branch
2. ✅ Jira ticket is marked "Done"
3. ✅ Feature branch is cleaned up
4. ✅ Changes are live (or queued for deployment)
5. ✅ Task is fully complete

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
6. /06-pr-review SOC-15                 # Review and improve code
7. /07-complete-task SOC-15             # Finish
  7.1. Verify PR is approved and checks are passing
  7.2. Merge PR and transition Jira to "Done"
  7.3. Clean up branches and sync
```

## Best Practices

### Before Running:

1. ✅ Ensure PR is approved by reviewers
2. ✅ Verify all checks are passing
3. ✅ Confirm no merge conflicts
4. ✅ Review final PR diff one last time
5. ✅ Check deployment readiness

### After Running:

1. ✅ Verify merge was successful
2. ✅ Check Jira ticket is "Done"

## Branch Protection

If repository has branch protection rules:

- Required reviewers must approve
- Required status checks must pass
- May require admin override for emergency merges
- May prevent deletion of protected branches

The skill respects all branch protection rules.

## Deployment Integration

### Automatic Deployment

If repository has CI/CD configured:

- Merge triggers deployment pipeline
- Skill reports deployment status
- Links to deployment logs/dashboard

### Manual Deployment

If manual deployment required:

- Skill notes "Pending deployment"
- Provides deployment instructions
- Links to deployment runbook

## Notes

- This skill should only run after `/06-pr-review` completes
- Only merges approved PRs with passing checks
- Follows repository's merge strategy preferences
- Respects all branch protection rules
- This is the ONLY skill that transitions Jira to "Done"
- Marks the official completion of development work
- Changes become permanent after merge

## Rollback Support

If issues are discovered after merge:

1. Create rollback PR:
   ```bash
   git revert <merge-commit-sha>
   git push origin main
   ```
2. Reopen Jira ticket with rollback details
3. Create new ticket for proper fix

## Success Criteria

A successful task completion includes:

✅ PR approved by required reviewers
✅ All status checks passing
✅ No merge conflicts
✅ PR merged to base branch
✅ Jira ticket transitioned to "Done"
✅ Final comment added to Jira
✅ Feature branch cleaned up (if configured)
✅ Deployment initiated (if configured)

## Troubleshooting

### "Cannot find PR"

- Ensure the feature branch follows the `feature/<JIRA-KEY>-description` naming convention
- Use `list_pull_requests` via GitHub MCP to verify open PRs for the branch
- Specify PR number explicitly as an argument

### "Not approved"

- Request reviews from team members
- Ensure required number of approvals met
- Check review status using `get_pull_request` via GitHub MCP

### "Checks failing"

- Fetch failing check details using `pull_request_read` (method `get_check_runs`) via GitHub MCP
- Fix issues and push changes
- Wait for checks to complete and re-verify

### "Merge conflict"

- Follow the **Sibling drift** steps in section 2: `git -C <repo> fetch origin main`, `git -C <repo> merge origin/main --no-edit`, resolve, install/build/test, `git -C <repo> push`, wait for CI

## Examples

### Example 1: Explicit Jira

```bash
/07-complete-task SOC-15

Verifying PR for SOC-15...
✅ All prerequisites met
✅ Merged successfully
✅ Jira updated

Task complete! 🎉
```

**Key improvement**: Ticket only marked "Done" AFTER the PR is merged, following standard SDLC practices.

---

## ⛔ Stop or Hand Off

This skill is now complete. What happens next depends **only** on a pipeline state file on disk, never on conversation history.

### 1. Locate the state file

Look for `.sdlc/<JIRA-KEY>.json` in the current working directory, then in each ancestor directory up to the project root (the directory this Claude session started in), **never above it**. This covers worktrees under `.worktrees/` and multi-repo parent directories. Use the `Read` tool (plus `Glob` if it is listed; otherwise `ls .sdlc/` run from each directory inside the project): looking above the project root prompts and can pick up an unrelated pipeline's file. Use the first file found.

### 2. Standalone mode (no state file, or the file fails validation)

If no file is found, or the file fails any check in step 3, you are in standalone mode. If a file was found but failed validation, first print one line naming the file and the failed check (wrong `jira_key`, `mode` not `chained`, or stage `07` not `in_progress`) so a stale file is noticed. Then:

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
- `stages["07"].status` is `"in_progress"`

**Compaction rule**: chained mode is decided by the file on disk and nothing else. Never continue because a summary says the next step was "pending". After any context compaction, re-read the file before acting. If the file says stage `07` is still `in_progress`, re-verify this stage's own outputs (comments posted, branches created, PRs opened, etc.) before marking it done.

### 4. Decide the outcome

This stage **halts** the pipeline if any of these occurred:

- Any pre-merge check fails (approval, status checks, conflicts, draft, permissions). An audit check the user accepted with **Merge anyway** in step 1 does not count as failing
- The user answered **Stop** to the override question
- The merge fails in any repo

> This is always the last stage. On success, run the **Finished** announcement. Never invoke anything after it.

### 5. Hand off or halt

Update the state file with the `Edit` tool (never a shell redirect) and take timestamps from `date -u +%Y-%m-%dT%H:%M:%SZ`.

**On success:**

1. Set `stages["07"].status = "done"` and `stages["07"].finished_at` in the state file.
2. This is always the final stage: run the **Finished** announcement from `/00-run-sdlc` ("Pipeline Announcements") and stop.

**On halt:**

1. Set `stages["07"].status = "failed"` and `halted = { "stage": "07", "reason": "<one line>", "at": "<timestamp>" }`.
2. Run the **Halted** announcement from `/00-run-sdlc` ("Pipeline Announcements").
3. Stop. Do NOT invoke the next stage. The user continues with `/00-run-sdlc <JIRA-KEY> --resume` after fixing the issue.
