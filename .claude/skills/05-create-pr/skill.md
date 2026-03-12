# Create Pull Request Skill

Commits your changes and creates a pull request for code review. This skill prepares your work for review WITHOUT marking the Jira ticket as "Done" - that happens after the PR is merged.

## Usage

```
/05-create-pr <JIRA-KEY> "<summary>"
```

### Examples

```bash
# Basic usage
/05-create-pr SOC-5 "Implemented Streamlit review interface"

# With more detail
/05-create-pr SOC-8 "Added LinkedIn API integration with OAuth2 flow and post scheduling"
```

## What It Does

Once complete, it executes the command `say finished creating the pull request for the task {SOC-XX}`, ensure to replace {SOC-XX} with the actual Jira key.

## What It Does Not

When creating the PR, it, in no way, provides any atrribution to Anthropic or Claude Code in the commit message, PR description, or Jira comments. This is a personal commit by the user.

### 1. Git Status Check

- Runs `git status` to see what files changed
- Runs `git diff` to review the actual changes
- **Determines commit state**:
  - If the working tree is clean AND commits exist ahead of `origin/main` → changes are already committed (common when `/03-dev-execute` has run). **Skip step 3 (Git Commit) and proceed directly to step 4 (Git Push).**
  - If unstaged or staged changes exist → commit as described in step 3.

### 2. Jira Update

- Fetches the current Jira issue details using the Atlassian MCP Server
- Adds a comprehensive comment with:
  - Work summary and file changes
  - Scope changes (if any) with rationales
  - Follow-up work identified
  - Known limitations
  - Metrics (LOC, test coverage, architectural decisions)
- **Transitions ticket to "In Review"** (if available) or keeps in "In Progress"
- Does NOT transition to "Done" - that happens after PR merge

### 3. Git Commit

- Generates a commit message following the format, do not provide any attribution to Claude in the commit message, as this is a personal commit by the user:

  ```
  [JIRA-KEY] Brief description

  Detailed changes:
  - Change 1
  - Change 2
  - Change 3

  Jira: https://[site].atlassian.net/browse/JIRA-KEY
  ```

- Commits all staged and unstaged changes
- Includes the Jira ticket link in the commit

### 4. Git Push

- Pushes the commit to the remote repository
- Reports the result

### 5. Create Pull Request

- Creates PR using GitHub MCP with:
  - Title from Jira ticket
  - Summary of changes from git log
  - Test plan section
  - Link to Jira ticket
- Links PR to Jira as remote issue link
- Posts PR link to Jira comments

## Prerequisites

- Jira MCP server configured in [.mcp.json](../.mcp.json)
- GitHub MCP server configured in [.mcp.json](../.mcp.json)
- Git repository initialized
- Git remote configured
- Working directory must have changes to commit

## Arguments

| Argument   | Required | Description                             | Example            |
| ---------- | -------- | --------------------------------------- | ------------------ |
| `jira_key` | Yes      | The Jira issue key (e.g., SOC-5)        | `SOC-5`            |
| `summary`  | Yes      | Brief description of the work completed | `"Implemented UI"` |

## Jira Status Transition Logic

The skill automatically determines the appropriate Jira transition:

- If "In Review" status exists → transitions to "In Review"
- Otherwise → keeps ticket in "In Progress"
- **Never** transitions to "Done" (that's for `/07-complete-task` after PR merge)

## Error Handling

The skill will:

- Stop if there are no changes to commit
- Report if Jira ticket doesn't exist
- Report if git push fails
- Report if PR creation fails
- Provide clear error messages at each step

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

## 🔗 Pull Request

Created PR for code review: [PR Link]
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
- Do NOT add co-authored-by or any Claude attribution to commit messages
- Jira comments include comprehensive completion details for traceability
- Scope changes are highlighted with clear rationales
- The commit message includes a link back to the Jira ticket
- Architectural decisions are counted and referenced
- **This skill does NOT close the Jira ticket** - that happens after PR merge in `/07-complete-task`

## Integration with Workflow

### Complete SDLC Workflow:

```bash
1. /02-start-task SOC-15              # Start work, Jira → "In Progress"
2. /03-dev-execute SOC-15             # Implement feature
3. /04-reconcile-work SOC-15          # Optional: Verify alignment
4. /05-create-pr SOC-15 "Done"        # Commit, push, create PR, Jira → "In Review"
5. /06-pr-review                      # Automated code review and improvements
6. /07-complete-task                  # Merge PR, Jira → "Done"
```

This ensures proper separation of:

- **Development** (02-03): Writing code
- **Quality Check** (04): Verifying requirements
- **Code Review** (05-06): PR creation and review
- **Deployment** (07): Merging and closing

## Difference from Old `/05-complete-task`

### Old Behavior (Incorrect):

```
/05-complete-task → Commit → Push → Jira → "Done" ✅
/06-pr-workflow → Create PR (ticket already closed!) ❌
```

### New Behavior (Correct):

```
/05-create-pr → Commit → Push → Create PR → Jira → "In Review" 🔍
/06-pr-review → Review and improve code 🔧
/07-complete-task → Merge PR → Jira → "Done" ✅
```

This follows standard SDLC where tickets are only marked "Done" **after** the PR is merged, not before.

---

## ⛔ Stop Here

This skill is now complete. **Do NOT invoke the next skill automatically.**

State what the recommended next step is for the user's reference, then stop and wait for the user to explicitly trigger it.
