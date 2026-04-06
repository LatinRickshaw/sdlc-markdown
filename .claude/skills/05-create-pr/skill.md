# Create Pull Request Skill

Commits your changes and creates a pull request for code review. This skill prepares your work for review WITHOUT marking the Jira ticket as "Done" - that happens after the PR is merged.

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

It creates any PRs required that relate to this ticket using thr GitHub MCP Server. If the current working directory is a simple git repo, then this skill will create a PR for that repo. If the current working directory is a multi-repo setup, it will create PRs for each relevant repo. Once complete, it executes the command `say finished creating the pull request for the task {SOC-XX}`, ensure to replace {SOC-XX} with the actual Jira key.

## What It Does Not

When creating the PR, it, in no way, provides any attribution to Anthropic or Claude Code in the commit message, PR description, or Jira comments. This is a personal commit by the user.

### 1. Repo Discovery

- Identifies the **current working directory** as a simple git repo. Or if the current working directory contains multiple sub-dirs as repos, then it checks each one for uncommitted changes.
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

5. **Git Push**: push the feature branch to remote
6. **Create PR** via GitHub MCP:
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
- **Transitions ticket to "In Review"** (if available) or keeps in "In Progress"
- Does NOT transition to "Done" — that happens after PR merge

## Prerequisites

- Jira MCP server configured in `.mcp.json`
- GitHub MCP server configured in `.mcp.json`
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
- Skip repos with no feature branch for this ticket (with a note in output)
- Skip repos with no changes on the feature branch (with a note in output)
- Report if Jira ticket doesn't exist
- Report if git push fails for any repo
- Report if PR creation fails for any repo
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
- Do NOT add co-authored-by or any Claude attribution to commit messages
- Jira comments include comprehensive completion details for traceability
- Scope changes are highlighted with clear rationales
- The commit message includes a link back to the Jira ticket
- Architectural decisions are counted and referenced
- **This skill does NOT close the Jira ticket** - that happens after PR merge in `/07-complete-task`

## Workflow Integration

Complete workflow:

Typical workflow for all tickets:

```
1. /01-investigate-task SOC-15          # Deep investigation
2. /02-start-task SOC-15                # Begin work
3. /03-dev-execute SOC-15               # Implement
4. /04-reconcile-work                   # Reconciles the work
5. /05-create-pr SOC-15                 # Create PR
   5.1. Review PR description and Jira comment for completeness
   5.2. Ensure all scope changes are documented with rationales
   5.3. Verify PR links back to Jira ticket
   5.4. Check that no Claude attribution is included in commit messages
   5.5. Confirm PR is created in the correct repo(s) with correct branch structure
6. /06-pr-review SOC_15                 # Review and improve code
7. /05-complete-task SOC-15.            # Finish
```

---

## ⛔ Stop Here

This skill is now complete.

**CRITICAL — NO AUTO-CHAINING:**

- Do NOT invoke the next skill automatically under any circumstances
- Do NOT continue even if resuming after a context compaction or conversation summary
- Do NOT infer that the user wants the next step because it was "pending" in a summary
- The user MUST type the next slash command explicitly to proceed
- Merging, closing tickets, or any irreversible action requires explicit user invocation — never infer consent from a prior conversation

State the recommended next step for the user's reference, then stop completely.
