# Reconcile Work Skill

Audits completed work against Jira ticket requirements to verify alignment and completeness. Use this before creating a PR or completing a task to ensure all requirements were met.

## Usage

```
/04-reconcile-work <JIRA-KEY>
```

### Examples

```bash
# Reconcile before creating PR
/04-reconcile-work SOC-15

# Audit work on current branch
/04-reconcile-work SOC-22
```

## What It Does

This skill performs a comprehensive audit of work completed on the current branch against the Jira ticket requirements. Once complete, it executes the command `say finished reconciling the task {SOC-XX}`, ensure to replace {SOC-XX} with the actual Jira key.

### 1. Fetch Ticket Requirements

- Retrieves Jira ticket with full description using the Atlassian MCP server
- Extracts all tasks/checkboxes from description
- Lists acceptance criteria
- Identifies key deliverables

### 2. Analyze Git History

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

1. **Generate detailed markdown report** - Save to `RECONCILIATION_REPORT_[JIRA-KEY].md` temporarily
2. **Post summary to Jira** - Add comment to the ticket using Atlassian MCP server
3. **Clean up** - Remove the markdown file from the codebase after posting to Jira
4. **Display summary** - Show key findings in terminal

This ensures the reconciliation is documented in Jira (the source of truth) without cluttering the codebase with temporary report files.

## When to Use This Skill

### Use /04-reconcile-work When:

**REQUIRED for:**

- Multi-day development (>3 days of work)
- Multiple commits with scope changes
- Work interrupted and resumed later
- Sprint demo preparation
- Complex tickets with many sub-tasks
- First time implementing this type of feature

**RECOMMENDED for:**

- Work with any scope additions/changes
- Unclear initial requirements (clarified during work)
- Want confidence before creating PR
- Team leads reviewing subordinate work
- Large refactoring efforts
- Cross-cutting changes affecting multiple modules

**SKIP for:**

- Single commit, simple fix
- Obvious 1:1 mapping to ticket requirements
- Already confident all requirements met
- Simple bug fixes or typo corrections
- Documentation-only changes
- Configuration changes with no business logic

### Quick Decision Guide

```
Is it multi-day work? ─── YES ──→ USE /04-reconcile-work
        │
        NO
        │
        ↓
Were there scope changes? ─── YES ──→ USE /04-reconcile-work
        │
        NO
        │
        ↓
Is it a complex feature? ─── YES ──→ USE /04-reconcile-work
        │
        NO
        │
        ↓
More than 3 commits? ─── YES ──→ CONSIDER /04-reconcile-work
        │
        NO
        │
        ↓
    SKIP (optional)
```

### Real-World Examples

**SOC-14** (Migration task):

- Single-commit migration
- Clear requirements from deprecation notice
- No scope changes
- One file modified (generator.py) + test updates
- **Decision**: ✅ Correctly SKIPPED reconciliation
- **Rationale**: Simple, focused change with clear requirements

**SOC-45** (Complex feature - hypothetical):

- 5 days of work
- 12 commits
- Scope expanded (added CLI features beyond requirements)
- 8 files created, 15 files modified
- **Decision**: ⚠️ SHOULD use reconciliation
- **Rationale**: Multi-day work with scope changes

**SOC-28** (Bug fix - hypothetical):

- 2-line change in error handler
- Single commit
- Obvious fix for reported issue
- **Decision**: ✅ Correctly SKIP reconciliation
- **Rationale**: Trivial fix with no scope concerns

**SOC-67** (Refactoring - hypothetical):

- 3 days of work
- 8 commits
- Extract service classes
- No new features, just restructuring
- **Decision**: ⚠️ SHOULD use reconciliation
- **Rationale**: Multi-day work affecting multiple files, need to verify all functionality preserved

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

### Recommended Flow:

```
1. /02-start-task SOC-15
2. /03-dev-execute SOC-15
3. /04-reconcile-work SOC-15         # Audit before creating PR
4. Review reconciliation report
5. Address any gaps or issues
6. /05-create-pr SOC-15 "Done"       # Create PR for review
7. /06-pr-review                     # Review and approve
8. /07-complete-task                 # Merge and close
```

### Sprint Retrospective:

```
# Reconcile all tickets from sprint
/04-reconcile-work SOC-12
/04-reconcile-work SOC-13
/04-reconcile-work SOC-14

# Analyze patterns:
- Which tickets had scope creep?
- Which had better estimates?
- What caused divergence?
```

## Error Handling

The skill will:

- Report if Jira ticket doesn't exist
- Handle branches without commits gracefully
- Note when ticket has no clear tasks/criteria
- Continue with partial data if some analysis fails
- Provide best-effort report even with incomplete data

## Notes

- This is an optional skill - not required for all tasks
- Most useful for complex or long-running work
- Helps identify patterns in estimation accuracy
- Valuable for sprint retrospectives and planning
- Can be run multiple times during development
- Report is a snapshot - rerun after additional commits
- Particularly useful for team leads and project managers

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

## Advanced Usage

### Compare Multiple Branches

```bash
# Switch branches and reconcile each
git checkout feature-a
/04-reconcile-work SOC-10

git checkout feature-b
/04-reconcile-work SOC-11

# Compare alignment scores
```

### Historical Analysis

```bash
# Reconcile closed tickets for retrospective
/04-reconcile-work SOC-5  # Closed last sprint
/04-reconcile-work SOC-8  # Closed last sprint

# Identify estimation patterns
```


---

## ⛔ Stop Here

This skill is now complete. **Do NOT invoke the next skill automatically.**

State what the recommended next step is for the user's reference, then stop and wait for the user to explicitly trigger it.
