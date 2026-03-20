# Complete Task Skill

Merges an approved pull request and marks the Jira ticket as "Done". This is the final step in the development workflow, executed after code review is complete.

## Usage

```
/07-complete-task [PR-NUMBER] [JIRA-KEY]
```

### Examples

```bash
# Complete task with current PR
/07-complete-task

# Complete specific PR
/07-complete-task 42

# Complete with explicit Jira key
/07-complete-task 42 SOC-15
```

## What It Does

Once complete, it executes the command `say finished completing the task {SOC-XX}`, ensure to replace {SOC-XX} with the actual Jira key.

### 1. PR Verification

- Fetches PR details using GitHub MCP
- Verifies PR is approved by required reviewers, OR confirms a ✅ ready-for-merge review summary comment was posted by `/06-pr-review` (covers solo repos where self-approval is blocked by GitHub)
- Checks that all status checks pass
- Confirms no merge conflicts exist
- Validates PR is in mergeable state

### 2. Merge Pull Request

- Merges PR using appropriate strategy:
  - **Squash merge** (default): Combines all commits into one clean commit
  - **Merge commit**: Preserves all commits (if repo configured)
  - **Rebase**: Rebases and fast-forwards (if repo configured)
- Uses GitHub MCP to execute merge
- Confirms merge was successful

### 3. Jira Finalization

- Fetches current Jira issue details using Atlassian MCP
- Adds final comment to Jira:
  - PR merged confirmation
  - Link to merged PR
  - Final commit SHA
  - Deployment status (if available)
- **Transitions Jira ticket to "Done"**
- Records completion timestamp

### 4. Cleanup (Optional)

- Optionally deletes remote feature branch (if configured)
- Optionally deletes local feature branch
- Switches back to main branch
- Syncs with remote

## Prerequisites

- GitHub MCP server configured in [.mcp.json](../.mcp.json)
- Jira MCP server configured in [.mcp.json](../.mcp.json)
- PR must be approved
- All status checks must pass
- No merge conflicts
- User must have merge permissions

## Arguments

| Argument    | Required | Description                          | Example  |
| ----------- | -------- | ------------------------------------ | -------- |
| `pr_number` | No       | PR number (auto-detected if omitted) | `42`     |
| `jira_key`  | No       | Jira key (auto-detected if omitted)  | `SOC-15` |

## Auto-Detection

The skill automatically detects:

- **PR number**: From current branch's open PR
- **Jira key**: From branch name (e.g., `feature/SOC-15-description`)

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
- ✅ Local branch deleted

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

## Integration with Workflow

### Complete SDLC Workflow:

```bash
1. /02-start-task SOC-15              # Start work, Jira → "In Progress"
2. /03-dev-execute SOC-15             # Implement feature
3. /04-reconcile-work SOC-15          # Optional: Verify alignment
4. /05-create-pr SOC-15 "Done"        # Commit, push, create PR, Jira → "In Review"
5. /06-pr-review                      # Automated code review and improvements
6. /07-complete-task                  # Merge PR, Jira → "Done" ✅
```

### Workflow States:

```
Development Phase:
  02-start-task        → Jira: "In Progress"
  03-dev-execute       → Code implementation
  04-reconcile-work    → Quality verification

Code Review Phase:
  05-create-pr         → Jira: "In Review", PR created
  06-pr-review         → Code review and improvements

Deployment Phase:
  07-complete-task     → PR merged, Jira: "Done" ✅
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
3. ✅ Monitor deployment pipeline
4. ✅ Confirm changes are live
5. ✅ Notify stakeholders if needed

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

- Ensure you're on a feature branch
- Check PR exists using `gh pr list`
- Specify PR number explicitly

### "Not approved"

- Request reviews from team members
- Ensure required number of approvals met
- Check review status with `gh pr view`

### "Checks failing"

- View failing checks with `gh pr checks`
- Fix issues and push changes
- Wait for checks to complete

### "Merge conflict"

- Pull latest from base branch
- Resolve conflicts locally
- Push resolved changes

## Examples

### Example 1: Standard Completion

```bash
# After PR is approved and checks pass
/07-complete-task

Verifying PR #42...
✅ Approved by 2 reviewers
✅ All checks passing
✅ No merge conflicts

Merging PR #42 using squash strategy...
✅ PR merged successfully (commit: abc123)

Updating Jira SOC-15...
✅ Transitioned to "Done"
✅ Final comment added

Cleaning up branches...
✅ Deleted remote branch feature/SOC-15-api
✅ Deleted local branch
✅ Switched to main

Task complete! 🎉
```

### Example 2: Explicit PR and Jira

```bash
/07-complete-task 42 SOC-15

Verifying PR #42 for SOC-15...
✅ All prerequisites met
✅ Merged successfully
✅ Jira updated

Task complete! 🎉
```

### Example 3: Checks Failing

```bash
/07-complete-task

Verifying PR #42...
❌ Cannot merge: Checks failing

Failed checks:
- ❌ Test Suite (3 tests failing)
- ❌ Lint (2 style violations)

Action required:
1. Fix failing tests in test_api.py
2. Run linter: npm run lint:fix
3. Push changes
4. Wait for checks to pass
5. Run /07-complete-task again
```

## Difference from Old Workflow

### Old Workflow (Incorrect):

```
/05-complete-task → Jira → "Done" ✅
/06-pr-workflow → Create & merge PR (ticket already closed!)
```

### New Workflow (Correct):

```
/05-create-pr → Create PR, Jira → "In Review" 🔍
/06-pr-review → Review and improve code 🔧
/07-complete-task → Merge PR, Jira → "Done" ✅
```

**Key improvement**: Ticket only marked "Done" AFTER the PR is merged, following standard SDLC practices.


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
