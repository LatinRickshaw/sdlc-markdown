# Pull Request Review Skill

**Automated PR code review with implementation of improvements and approval.**

This skill conducts comprehensive code review of a pull request, implements recommended improvements, and approves the PR when ready. It does NOT merge the PR - that's handled by `/07-complete-task`.

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

```bash
# Review PR for specific Jira ticket
/06-pr-review SOC-5
```

## What This Skill Does

This skill performs a critical review any open PRs for the ticket referenced. Once complete, it executes the command `say finished reviewing the pull request for the task {SOC-XX}`, ensure to replace {SOC-XX} with the actual Jira key.

### Phase 1: Discover & Fetch PR Details

1. Identifies the **current working directory** as a simple git repo. Or if the current working directory contains multiple sub-dirs as repos, then it checks each one for open PRs.
2. Builds a list of all sibling repos (same multi-repo logic as `/02-start-task`)
3. For each repo, searches for an open PR whose head branch matches `feature/<JIRA-KEY>` using the GitHub MCP
4. Fetches PR details for each found PR: title, description, status, checks using GitHub MCP
5. Retrieves diff and files changed for each PR using GitHub MCP
6. Gets linked Jira ticket details (if available) using Atlassian MCP

### Phase 2: Automated Code Review

Analyzes all touched files comprehensively — not just lines introduced by this PR. The goal is the **highest possible code quality**, so any issue found in a file is in scope regardless of when it was introduced.

- **Critical Issues**: Missing dependencies, breaking changes, security concerns
- **Code Quality**: Type safety, error handling, import organization
- **Documentation**: README updates, docstrings, comments
- **Testing**: Test coverage, edge cases, integration tests
- **Architecture**: Type definitions, code organization, patterns

> **Important**: Do not limit the review to diff lines. If a pre-existing bug, missing test, or quality gap is found anywhere in a touched file, it must be flagged and fixed. The fact that this PR did not introduce the issue is irrelevant — shipping high-quality code is the standard.

> **Exception — dependency-only PRs:** if the diff touches only `package.json` and the lockfile (`yarn.lock`, `package-lock.json`), use the **Dependency-only fast path** below instead of the full-file review. Do not "fix" pre-existing issues in those files: editing unrelated `resolutions` or version ranges re-resolves other packages and widens the change.

Generates detailed review with categorized recommendations.

### Phase 3: Implement Recommendations

1. Creates todo list from review recommendations
2. Implements each recommendation systematically, including **pre-existing issues** found during review:
   - Type safety improvements
   - Error handling enhancements
   - Documentation updates
   - Test coverage additions
   - Code organization refactoring
3. Organizes changes into logical commits
4. Pushes commits to PR branch

> **Reminder**: Fixes for pre-existing issues belong in this PR. The bar is overall code quality, not authorship of the defect.

### Phase 3b: CI Checks & PR Tasks Verification

After pushing, verify all checks and tasks pass before proceeding to approval:

> **Important**: Every failing check is a blocker, whether or not this PR caused it. Fix any failing check whose cause is in code or config (tests, lint, types, build), including pre-existing ones. The one exception is a **pre-existing audit failure**, described below. It is documented and halts the run, and this stage does not try to fix it.

1. Fetch all PR checks with the **CI waiting procedure** (below)
2. Fetch all PR tasks/to-do items (checklist items in PR description) using GitHub MCP
3. For each **failed or errored check** (whether introduced by this PR or pre-existing):
   - Identify the root cause by reading the check's log output
   - **Audit-type check** (Security Scans, `yarn audit`, `npm audit`, dependency review): compute the **Advisory-ID diff** (below) first.
     - If the diff shows `new` advisories, this PR caused them. Fix them like any other failure.
     - If `new` is empty, the failure is **pre-existing**: the same advisories are red on `main`. Do not fix it here, because that widens the PR beyond its ticket. Post the diff in the PR summary comment and halt (see "Decide the outcome"). `/07-complete-task` asks the user whether to override.
   - Any other check: fix the underlying issue (e.g. failing tests, lint errors, type errors, build failures)
   - Commit and push the fix (`git -C <repo> push`)
   - Wait for the check to re-run with the CI waiting procedure and confirm it passes
4. For each **incomplete PR task** (unchecked checklist item in the PR body, regardless of origin):
   - Determine whether it can be completed programmatically (e.g. "add tests", "update docs")
   - If so, complete the work, commit, and push
   - If it requires human action, flag it explicitly in the PR summary comment
5. Repeat until **all checks are green** and **all automatable tasks are checked off**
6. If a check cannot be fixed after investigation, document the blocker clearly in the PR summary comment and do NOT approve

> **Important**: Do not proceed to Phase 4 (Approval) until all required checks pass and all automatable PR tasks are complete — including any that existed before this PR was opened.

> **HARD GATE before Phase 4:** If any check is still failing for any reason, do NOT post a ✅ ready-for-merge comment and do NOT mark the PR as ready. That includes a documented pre-existing audit failure. Repeat the process until all PR checks are green; only proceed to Phase 4 when all checks are green. For a pre-existing audit failure, post the summary comment with the advisory-ID diff and a ⛔ "blocked: pre-existing audit failure" status instead, then halt.

### Phase 4: Approval & Finalization

1. Adds summary comment to PR with completion status using GitHub MCP
2. Approves PR using GitHub MCP — **Note**: GitHub prevents self-approval. If the repository has no external reviewer configured, skip the formal approval and ensure the summary comment (step 1) clearly states the PR is ✅ ready for merge. Do NOT attempt a formal approval that will fail.
3. **Does NOT merge** - merging happens in `/07-complete-task`
4. Reports PR is ready for final review and merge

## Parameters

| Parameter  | Required | Description                        | Example |
| ---------- | -------- | ---------------------------------- | ------- |
| `jira_key` | Yes      | Jira ticket key to provide context | `SOC-5` |

## Workflow Steps

### Step 1: Identify PRs

1. Run `git branch --show-current` to get the current branch
2. Discover all sub repos in the current working directory
3. For each repo, use `list_pull_requests` via GitHub MCP (filtered by the `feature/<JIRA-KEY>` head branch) to find open PRs
4. Compile the full list of PRs to review across all repos

If no PRs are found:

- Reports error
- Suggests running `/05-create-pr` first

### Step 2: Conduct Code Review

Using GitHub MCP:

- Fetch PR diff and files changed
- For each changed file, analyze the **full file** (not just the diff), including:
  - Missing dependencies
  - Type safety issues
  - Error handling gaps
  - Documentation needs
  - Test coverage
  - Code organization
- Flag and fix issues regardless of whether this PR introduced them — if it's in a touched file, it's in scope
- Generate categorized recommendations

### Step 3: Implement Recommendations

For each recommendation:

1. Add to todo list
2. Mark as in_progress
3. Implement the change:
   - Edit files
   - Add tests
   - Update documentation
4. Mark as completed
5. Create focused commit

Example implementation order:

1. Type safety (TypedDict, remove casts)
2. Error handling (try/catch, validation)
3. Code organization (imports, structure)
4. Documentation (README, docstrings)
5. Testing (unit tests, integration tests)

### Step 4: Verify CI Checks & PR Tasks

After pushing recommendation commits:

- Fetch all check runs for the PR's head SHA with the **CI waiting procedure** below (GitHub MCP `pull_request_read`, method `get_check_runs`)
- Fetch PR details including the task checklist using `pull_request_read` (method `get`) via GitHub MCP
- For each failing check: read the log, diagnose, fix, push, and wait for the re-run. The exception is a pre-existing audit failure: compute the advisory-ID diff, document it, and halt (Phase 3b)
- For each PR task (checklist item in description, regardless of origin): complete automatable ones; flag manual ones
- Repeat until all checks are passing (verified with `get_check_runs`)
- Do NOT advance to Step 5 if any check is still failing. The cause of the failure is irrelevant
- Repeat the process of fixing issues and verifying checks until a green PR is achieved

### CI waiting procedure

CI is read through the GitHub MCP only. Never use the `gh` CLI, even if it is installed.

1. Call `pull_request_read` with method `get_check_runs` for the PR.
2. If any run is `queued` or `in_progress`, start `sleep 90` as a **background** Bash call (`run_in_background`). Poll again when it finishes. Lint/Test typically take 45–75 s, E2E about 80 s, and Security Scans about 30 s. Give up after about 20 minutes and report the check as stuck.
3. If the list of check runs is **empty**, fetch the PR (`pull_request_read`, method `get`) and look at `mergeable_state`:
   - `dirty`: the PR conflicts with its base, and GitHub runs no CI on a conflicted PR. Bring main in with `git -C <repo> fetch origin main` and `git -C <repo> merge origin/main --no-edit`, resolve the conflicts, then install, build and test using the command shapes, `git -C <repo> push`, and restart this procedure.
   - `unknown`: GitHub is still computing mergeability. Re-fetch the PR after the next background sleep.
   - anything else, still with no runs after 3 polls: the repo has no CI for this PR. Note that in the summary comment.
4. Done when every run has `status: completed`. Then evaluate each `conclusion`.

### Advisory-ID diff

Run this for each repo with a failing audit-type check, and also as part of the Dependency-only fast path.

1. **Branch side**: run the audit in the PR's checkout:
   - yarn classic: `yarn --cwd <repo> audit --json | jq -r 'select(.type=="auditAdvisory") | .data.advisory.github_advisory_id // .data.advisory.id' | sort -u`
   - yarn berry: `cd <repo> && corepack yarn npm audit --all --recursive --json`, then extract the advisory IDs with `jq`. If you are unsure of the output shape, inspect one line first with `| head -1`.
2. **Main side**: run the same command in a checkout of `main`. In worktree mode that is the main working tree, which sits on `main`. Without a `main` checkout, read the advisory IDs from the log of the same check on `main`'s latest commit via the GitHub MCP, and note that in the comment.
3. Compare the two sets:
   - `new`: on the branch only
   - `fixed`: on main only
   - `unchanged`: on both
4. Post the diff as a table in the PR summary comment. In chained mode, pass it to `state halt --advisory-diff` (see "Hand off or halt"), which records it in `halted.advisory_diff` keyed by repo name, with a one-line `--reason` such as `pre-existing audit failure in api: 0 new, 2 fixed, 5 unchanged advisories`.

### Dependency-only fast path

Use this when the PR diff touches **only** `package.json` and the lockfile (for example a bump or a `resolutions` pin for a vulnerable package). It replaces the full-file review in Phase 2. The review checks three things:

1. **Lockfile scope**: `git -C <repo> diff origin/main...HEAD -- yarn.lock` changes only entries for the target package family (the package and its own transitive dependencies). Any unrelated entry that was re-resolved is a finding. Revert it, don't add to it.
2. **One entry per target**: each target package resolves to exactly one version in the lockfile (`yarn --cwd <repo> why <pkg>` or `cd <repo> && corepack yarn why <pkg>`).
3. **Advisory-ID diff is clean**: the advisories the ticket targets appear under `fixed`, and `new` is empty.

Do not edit unrelated `resolutions`, version ranges or other "pre-existing issues" in `package.json`.

### Step 5: Finalize PR

- Push all commits
- Add summary comment to PR using GitHub MCP (include check status and task completion summary)
- Approve PR (if all checks pass and recommendations met) using GitHub MCP
- **Report that PR is ready for merge** (does not merge automatically)

## Review Categories

### Critical Issues (Must Fix)

- Missing required files/dependencies
- Breaking changes
- Security vulnerabilities
- Type errors
- Test failures

### Code Quality (Should Fix)

- Type safety improvements
- Error handling
- Import organization
- Code duplication
- Performance concerns

### Documentation (Should Add)

- README updates for new features
- API documentation
- Usage examples
- Configuration documentation

### Testing (Should Add)

- Unit tests for edge cases
- Integration tests
- Error handling tests
- Mock/fixture improvements

### Architecture (Consider)

- Type definitions (TypedDict, etc.)
- Code organization
- Design patterns
- Separation of concerns

## Output Format

The skill generates a structured review:

```markdown
## PR Review for SOC-X

### Overall Assessment

[Summary of PR quality and readiness]

### Critical Issues (X found)

1. Issue description
   - Impact: [High/Medium/Low]
   - Files: [affected files]
   - Recommendation: [specific fix]

### Code Quality Issues (X found)

[Categorized improvements]

### Documentation Gaps (X found)

[Missing or needed docs]

### Testing Improvements (X found)

[Test coverage needs]

### Recommendations Summary

**Before merging:**

- [ ] MUST: Fix critical issue X
- [ ] SHOULD: Improve Y
- [ ] CONSIDER: Refactor Z

**Estimated effort:** X hours
```

## Implementation Example

### Scenario: Review and Fix PR

```bash
# Start workflow for current branch
/06-pr-review SOC-15

# Skill fetches PR
Found PR #2 for SOC-15
Reviewing PR #2: [SOC-15] Implement Platform-Specific Templates

# Skill conducts review
Reviewing code changes...
Found 12 recommendations across 5 categories

# Skill creates todo list
✓ Added 12 todos for implementation

# Skill implements recommendations
[1/12] Adding TypedDict for PLATFORM_SPECS...
✓ Completed

[2/12] Removing cast() calls...
✓ Completed

[3/12] Adding YAML error handling...
✓ Completed

# ... continues through all recommendations

# Skill organizes commits
✓ Created 3 logical commits:
  - Refactor: Type safety improvements
  - Add: Comprehensive test coverage
  - Docs: Update README with new features

# Skill pushes and finalizes
✓ Pushed commits to PR
✓ Added summary comment
✓ All recommendations implemented
✓ PR approved

PR is ready for merge. Run /07-complete-task to merge and close ticket.
```

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
  6.1. Review PR details and files changed
  6.2. Conduct comprehensive code review (not limited to diff lines)
  6.3. Implement all recommendations, including fixes for pre-existing issues
  6.4. Verify all checks pass and all PR tasks are complete
  6.5. Approve PR when ready
7. /07-complete-task SOC-15             # Finish
```

## Prerequisites

- GitHub MCP server configured in `.mcp.json`
- Git repository with remote configured
- PRs must already exist (created by `/05-create-pr`)
- Proper branch naming convention (`feature/JIRA-KEY-description`)
- **Never push fix commits to a trunk branch** — the skill will abort if the current branch is `main`/`master`/`trunk`

## Error Handling

The skill handles common errors:

- **No PR exists**: Reports error, suggests running `/05-create-pr`
- **PR already merged**: Informs user, exits gracefully
- **Merge conflicts**: Provides resolution guidance
- **Check failures**: Reports failing checks
- **API rate limits**: Implements exponential backoff
- **Permission errors**: Clear error messages with resolution steps

## Best Practices

### For Best Results:

1. **Run after `/05-create-pr`**: Ensures PR exists
2. **Review suggestions carefully**: Not all recommendations may apply
3. **Keep PRs focused**: Smaller PRs get better reviews
4. **Address critical issues first**: Prioritize security and breaking changes
5. **Update Jira context**: Helps provide better recommendations

### Review Quality Tips:

- Review considers existing codebase patterns
- Balances thoroughness with practicality
- Prioritizes critical issues over style
- Provides specific, actionable recommendations
- Includes code examples where helpful

## What This Skill Does NOT Do

- ❌ Does NOT merge the PR (that's the job of `/07-complete-task`)
- ❌ Does NOT transition Jira to "Done" (that's the job of `/07-complete-task`)
- ❌ Does NOT delete branches (that's the job of `/07-complete-task`)
- ❌ Does NOT create the PR (that's the job of `/05-create-pr`)

## What Happens Next

After this skill completes:

1. ✅ PR has been reviewed comprehensively
2. ✅ Recommendations have been implemented
3. ✅ PR is approved and ready for merge
4. ⏭️ **Next step**: Run `/07-complete-task` to merge PR and mark Jira as "Done"

## Limitations

- Requires GitHub MCP server access
- Only works with GitHub repositories
- Cannot review images or binary files in detail
- Limited to repositories user has write access to
- Review quality depends on code complexity

## Examples

### Example 1: Standard Review

```bash
# After creating PR with /05-create-pr
/06-pr-review SOC-15

Found PR #2 for JIRA ticket SOC-15
Reviewing PR #2: [SOC-15] Implement Platform-Specific Templates

Analyzing code...
Found 9 recommendations

Implementing recommendations...
✓ 1/9 Type safety improvements
✓ 2/9 Error handling
✓ 3/9 Documentation updates
✓ 4/9 Test coverage
# ... continues ...

✓ All recommendations implemented
✓ 3 commits pushed
✓ PR approved

PR is ready for merge. Run /07-complete-task when ready.
```

## Troubleshooting

### Review Doesn't Find PRs

- Ensure `/05-create-pr` has been run and PRs were created
- Verify the feature branch naming follows `feature/<JIRA-KEY>-description`
- Confirm GitHub MCP server is running and authenticated

### Review Doesn't Find Issues

- Ensure PR has actual code changes
- Check file diff is accessible via `get_pull_request` (GitHub MCP)
- Verify GitHub MCP server is running

### Implementation Fails

- Check for merge conflicts
- Ensure working directory is clean
- Verify pre-commit hooks pass

### Cannot Approve PR (solo repo — expected behaviour)

- GitHub blocks self-approval; this is expected in solo repos
- This is NOT an error — post a clear ✅ ready-for-merge summary comment instead
- Ensure PR is not in draft state (genuine blocker)

## Success Criteria

A successful PR review completion includes:

✅ PR fetched and analyzed successfully
✅ Comprehensive review conducted across full file contents (not just diff lines)
✅ All critical issues resolved — including pre-existing ones in touched files
✅ Code quality improvements implemented regardless of who introduced them
✅ Documentation updated
✅ Test coverage adequate
✅ All CI checks passing (no failed or errored check runs)
✅ All automatable PR tasks/checklist items completed
✅ Any non-automatable PR tasks flagged in summary comment
✅ Clean commit history
✅ PR summary comment added confirming readiness for merge (including check status)
✅ PR approved via formal GitHub approval OR (for solo repos) via clear ✅ summary comment
✅ Ready for merge in `/07-complete-task`

## Notes

- This skill is designed for **automated review and improvement**
- It complements (doesn't replace) human code review
- Focuses on objective, automatable improvements
- Best used after `/05-create-pr`
- Ensures consistent code quality standards
- Does NOT merge the PR - that's the next step

**Built to ensure high-quality PRs with comprehensive automated review and improvement**

---

## ⛔ Stop or Hand Off

This skill is now complete. What happens next depends **only** on the pipeline state file `.sdlc/<JIRA-KEY>.json` on disk, never on conversation history. The pipeline script owns that file's `stages`, `current_stage`, `halted`, `completed_at` and `notes`: change them only through the commands below, never with the `Edit` tool.

### 1. Locate the state file

Run this from the project root (the directory this Claude session started in):

```
python3 -I .claude/sdlc/sdlc.py state locate <JIRA-KEY> --stage 06
```

It looks for `.sdlc/<JIRA-KEY>.json` in the current working directory, then in each ancestor directory up to the project root, **never above it**, and validates what it finds. It prints `"mode": "chained"` only if all of these hold:

- `mode` is `"chained"`
- `jira_key` equals the Jira key this skill was invoked with
- `stages["06"].status` is `"in_progress"`

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

**Compaction rule**: chained mode is decided by the file on disk and nothing else. Never continue because a summary says the next step was "pending". After any context compaction, run `state locate` again so you re-read the file before acting. If it says stage `06` is still `in_progress`, re-verify this stage's own outputs (comments posted, branches created, PRs opened, etc.) before advancing.

### 4. Decide the outcome

This stage **halts** the pipeline if any of these occurred:

- Any CI check is still failing after your fix attempts
- A check fails with a **pre-existing audit failure**. The advisory-ID diff has already been computed and posted in the PR comment (Phase 3b), so the halt costs only the override question in `/07-complete-task`. Do not try to fix it here
- A blocker had to be documented in the PR summary comment
- The PR is already merged

> **Merge guard**: hand off to `/07-complete-task` **only if the state file says `"until": "07"`**. `state advance` enforces this: it names `07-complete-task` as `next` only when `until` is `"07"`. With the default `until` of `06` it prints `"finished": true` instead, and this stage is the last one. Do NOT invoke `07-complete-task` unless `state advance` names it. The user merges with `/07-complete-task` themselves.

### 5. Hand off or halt

**On success:** run

```
python3 -I .claude/sdlc/sdlc.py state advance <JIRA-KEY> 06
```

It sets `stages["06"].status = "done"` and prints one of:

- `"next": {"skill": …, "args": …}`: Only if `until` is `"07"`. The script has already set stage `07` to `in_progress` and made it `current_stage`. Invoke exactly that skill with exactly those args via the Skill tool, and nothing else. For this stage that is skill `07-complete-task`, args `<JIRA-KEY>`.
- `"finished": true`: `until` was `"06"` (the default) and the script has run the **Finished** announcement. Print its `message` and stop.

**On halt:** run

```
python3 -I .claude/sdlc/sdlc.py state halt <JIRA-KEY> 06 --reason "<one line>"
```

For a pre-existing audit failure, first write the advisory-ID diff to the session scratchpad with the `Write` tool, as `{ "<repo>": { "new": [], "fixed": [...], "unchanged": [...] } }`, and add `--advisory-diff <scratchpad>/advisory-diff.json`. The script stores it as `halted.advisory_diff` (the `"advisory_diff"` key), so `/07-complete-task` can ask the override question without re-running the audit.

It sets `stages["06"].status = "failed"` and `halted`, then runs the **Halted** announcement. Print its `message`, then stop. Do NOT invoke the next stage. The user continues with `/00-run-sdlc <JIRA-KEY> --resume` after fixing the issue.

If either command exits 1, print its `reason` and stop. Never edit the state file to get around it.
