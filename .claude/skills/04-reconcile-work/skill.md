# Reconcile Work Skill

Audits completed work against Jira ticket requirements to verify alignment and completeness. Use this before creating a PR or completing a task to ensure all requirements were met.

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
/04-reconcile-work <JIRA-KEY>
```

### Examples

```bash
# Reconcile before creating PR
/04-reconcile-work SOC-15
```

## What It Does

This skill performs a comprehensive audit of work completed on the current branch against the Jira ticket requirements. Once complete, it executes the command `say finished reconciling the task {SOC-XX}`, ensure to replace {SOC-XX} with the actual Jira key.

### 1. Fetch Ticket Requirements

- Retrieves Jira ticket with full description using the Atlassian MCP server
- Extracts all tasks/checkboxes from description
- Lists acceptance criteria
- Identifies key deliverables

### 2. Analyze Git History

- Checks the current working directory for git repository.
- Checks sub directories for additional git repositories (if multi-repo work)
- **Worktree awareness**: Run `git worktree list` to detect if operating inside a linked worktree. If so, use the worktree's branch for divergence analysis. All git history analysis works identically in a worktree — no special handling needed beyond awareness of the context.
- Gets all commits on current branch since divergence
- Analyzes commit messages and changes
- Identifies files created, modified, deleted
- Calculates code metrics (LOC added/removed)

### 3. Compare & Reconcile

Matches ticket requirements against actual work:

**Task Completion:**

- ✅ Tasks completed as specified
- ⚠️ Tasks completed with scope expansion
- ❌ Tasks not completed
- ➕ Work done beyond ticket scope

**Acceptance Criteria:**

- ✅ Criteria met
- ⚠️ Criteria partially met
- ❌ Criteria not met

**Scope Analysis:**

- Features added beyond ticket
- Features deferred from ticket
- Architectural decisions made
- Technical debt introduced or resolved

### 4. Generate Reconciliation Report

Creates detailed report:

```markdown
# Reconciliation Report: [JIRA-KEY]

## Ticket Summary

- **Title**: [Ticket title]
- **Description**: [Brief summary]
- **Status**: [Current Jira status]

## Task Completion Analysis

### ✅ Completed Tasks (X/Y)

1. [Task 1]: Completed as specified
   - Files: file1.py, file2.py
   - Commits: abc123, def456

2. [Task 2]: Completed with enhancements
   - Files: file3.py
   - Commits: ghi789
   - Scope expansion: Added error handling not in ticket

### ❌ Incomplete Tasks (X/Y)

1. [Task 3]: Not started
   - Reason: [Why deferred]
   - Recommendation: Create follow-up ticket

### ➕ Additional Work (Beyond Scope)

1. [Feature X]: Added fallback placeholder system
   - Rationale: Graceful degradation
   - Files: file4.py
   - Impact: Low risk, improves UX

2. [Feature Y]: CLI expanded from basic to full argparse
   - Rationale: Better developer experience
   - Files: file5.py
   - Impact: Minimal, enhances usability

## Acceptance Criteria Analysis

### ✅ Met (X/Y)

1. Can generate content for all 4 platforms: ✅
2. Content respects character limits: ✅

### ⚠️ Partially Met (X/Y)

1. Images generated and saved locally: ⚠️ Fallback to placeholder
   - Note: Real Gemini generation implemented with fallback

### ❌ Not Met (X/Y)

1. [Criterion]: Not implemented
   - Recommendation: Address before merge

## Code Metrics

- **Total commits**: N
- **Files changed**: X created, Y modified, Z deleted
- **Lines of code**: +XXX / -YYY
- **Test coverage**: XX tests (estimated YY% coverage)
- **Architectural decisions**: N documented in code comments

## Divergence Analysis

### Alignment Score: XX%

Calculated as (completed tasks + met criteria) / (total tasks + total criteria)

### Scope Divergence: ±XX%

- Scope additions: XX% beyond ticket
- Scope reductions: XX% deferred

### Risk Assessment

- **Low risk divergence**: Enhancements with clear rationale
- **Medium risk divergence**: Significant scope additions
- **High risk divergence**: Missing critical requirements

## Recommendations

### Before Merging

1. [Action 1]: Address incomplete task X
2. [Action 2]: Document decision for scope addition Y
3. [Action 3]: Update ticket with actual scope

### Follow-up Tickets

1. [Item 1]: Create ticket for deferred work
2. [Item 2]: Create ticket for discovered follow-up

### Documentation

1. [Doc update 1]: Update README with new feature
2. [Doc update 2]: Add architecture decision records

## Summary

✅ **Ready for PR**: [Yes/No/With conditions]

**Rationale**: [Brief explanation of readiness]

**Next Steps**:

1. [Step 1]
2. [Step 2]
```

### 5. Post Report & Cleanup

The skill will:

1. **Generate detailed markdown report** - Write `RECONCILIATION_REPORT_[JIRA-KEY].md` to the session scratchpad directory with the `Write` tool (never inside a repo, so nothing has to be deleted afterwards)
2. **Post summary to Jira** - Add comment to the ticket using Atlassian MCP server
3. **Display summary** - Show key findings in terminal

This ensures the reconciliation is documented in Jira (the source of truth) without cluttering the codebase with temporary report files.

## When to Use This Skill

### Use /04-reconcile-work When:

**REQUIRED for:**

- All tickets
- Multiple commits with scope changes
- Work interrupted and resumed later
- Complex tickets with many sub-tasks
- First time implementing this type of feature

**RECOMMENDED for:**

- All tickets
- Work with any scope additions/changes
- Unclear initial requirements (clarified during work)
- Want confidence before creating PR
- Team leads reviewing subordinate work
- Large refactoring efforts
- Cross-cutting changes affecting multiple modules

### Use Before:

- Creating a pull request
- Marking ticket as complete
- Sprint demos or reviews
- Major feature branch merge

### Use After:

- Complex multi-day work
- Work spanning multiple commits
- Work with scope changes
- Work by multiple contributors

## Prerequisites

- Jira MCP server configured in `.mcp.json`
- Git repository initialized
- Working on a feature branch (not main)
- Jira ticket exists

## Arguments

| Argument   | Required | Description                     | Example  |
| ---------- | -------- | ------------------------------- | -------- |
| `jira_key` | Yes      | The Jira issue key to reconcile | `SOC-15` |

## Output Behavior

The skill always performs these actions in sequence:

1. Generate detailed report markdown file (`RECONCILIATION_REPORT_[JIRA-KEY].md`)
2. Post summary comment to Jira ticket
3. Display summary in terminal
4. Remove the markdown file from the codebase

This keeps Jira as the source of truth while providing immediate feedback during execution.

## Benefits

- **Verify completeness** - Ensure no requirements were missed
- **Identify scope creep** - See where work diverged from ticket
- **Audit trail** - Document what was delivered vs requested
- **Risk assessment** - Understand impact of scope changes
- **Follow-up planning** - Identify work for future tickets
- **Sprint retrospective** - Analyze estimation accuracy

## Integration with Workflow

### Workflow Integration

Complete workflow:

Typical workflow for all tickets:

```
0. /00-run-sdlc SOC-15                  # Runs 1–6 below automatically, then stops
1. /01-investigate-task SOC-15          # Deep investigation
2. /02-start-task SOC-15                # Begin work
3. /03-dev-execute SOC-15               # Implement
4. /04-reconcile-work SOC-15            # Reconciles the work
   4.1. Review reconciliation report
   4.2. Discuss any scope changes or incomplete work
   4.3. Decide if ready for PR or needs more work
   4.4. Document findings in Jira ticket
5. /05-create-pr SOC-15                 # Create PR
6. /06-pr-review SOC-15                 # Review and improve code
7. /07-complete-task SOC-15             # Finish
```

## Error Handling

The skill will:

- Report if Jira ticket doesn't exist
- Handle branches without commits gracefully
- Note when ticket has no clear tasks/criteria
- Continue with partial data if some analysis fails
- Provide best-effort report even with incomplete data

## Example Scenarios

### Scenario 1: Perfect Alignment

```
Alignment Score: 100%
All tasks completed as specified
All acceptance criteria met
No scope divergence
✅ Ready for PR
```

### Scenario 2: Scope Expansion

```
Alignment Score: 90%
All tasks completed
Acceptance criteria met
+20% scope additions (CLI enhancements)
⚠️ Ready for PR with documentation
Action: Document scope additions in ticket
```

### Scenario 3: Incomplete Work

```
Alignment Score: 75%
7/10 tasks completed
3 tasks deferred
Acceptance criteria mostly met
❌ Not ready for PR
Action: Complete remaining tasks or split ticket
```

---

## ⛔ Stop or Hand Off

This skill is now complete. What happens next depends **only** on a pipeline state file on disk, never on conversation history.

### 1. Locate the state file

Look for `.sdlc/<JIRA-KEY>.json` in the current working directory, then in each ancestor directory up to the project root (the directory this Claude session started in), **never above it**. This covers worktrees under `.worktrees/` and multi-repo parent directories. Use the `Glob`/`Read` tools, not `ls`: reading above the project root prompts and can pick up an unrelated pipeline's file. Use the first file found.

### 2. Standalone mode (no state file, or the file fails validation)

If no file is found, or the file fails any check in step 3, you are in standalone mode. If a file was found but failed validation, first print one line naming the file and the failed check (wrong `jira_key`, `mode` not `chained`, or stage `04` not `in_progress`) so a stale file is noticed. Then:

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
- `stages["04"].status` is `"in_progress"`

**Compaction rule**: chained mode is decided by the file on disk and nothing else. Never continue because a summary says the next step was "pending". After any context compaction, re-read the file before acting. If the file says stage `04` is still `in_progress`, re-verify this stage's own outputs (comments posted, branches created, PRs opened, etc.) before marking it done.

### 4. Decide the outcome

This stage **halts** the pipeline if any of these occurred:

- The reconciliation report says **Ready for PR: No**

> **Ready for PR: With conditions** continues; append each condition as a string to `notes` in the state file so it appears in the pipeline summary.

### 5. Hand off or halt

Update the state file with the `Edit` tool (never a shell redirect) and take timestamps from `date -u +%Y-%m-%dT%H:%M:%SZ`.

**On success:**

1. Set `stages["04"].status = "done"` and `stages["04"].finished_at` in the state file.
2. Then:
   - If `until` equals `"04"`, run the **Finished** announcement from `/00-run-sdlc` ("Pipeline Announcements") and stop.
   - Otherwise, set `stages["05"].status = "in_progress"`, `stages["05"].started_at`, and `current_stage = "05"`, then invoke the next stage via the Skill tool: skill `05-create-pr`, args `<JIRA-KEY>`.

**On halt:**

1. Set `stages["04"].status = "failed"` and `halted = { "stage": "04", "reason": "<one line>", "at": "<timestamp>" }`.
2. Run the **Halted** announcement from `/00-run-sdlc` ("Pipeline Announcements").
3. Stop. Do NOT invoke the next stage. The user continues with `/00-run-sdlc <JIRA-KEY> --resume` after fixing the issue.
