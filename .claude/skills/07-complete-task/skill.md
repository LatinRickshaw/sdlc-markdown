# Complete Task Skill

Merges an approved pull request and marks the Jira ticket as "Done". This is the final step in the development workflow, executed after code review is complete.

## Usage

```
/07-complete-task [PR-NUMBER] [JIRA-KEY]
```

### Examples

```bash
# Complete with explicit Jira key
/07-complete-task 42 SOC-15
```

## What It Does

Marges any open PRs relating to this ticket. Transitions the relevant ticket in JIRA. Once complete, it executes the command `say finished completing the task {SOC-XX}`, ensure to replace {SOC-XX} with the actual Jira key.

### 1. Repo & PR Discovery

- Identifies the **current working directory** and scans all sub repos for git repositories (same discovery logic as `/02-start-task`)
- For each repo, uses `list_pull_requests` via GitHub MCP (filtered by `feature/<JIRA-KEY>` head branch) to find open PRs
- Compiles the full list of PRs to merge across all repos

### 2. PR Verification (per repo)

For each discovered PR:

- Fetches PR details using GitHub MCP
- Verifies PR is approved by required reviewers, OR confirms a ✅ ready-for-merge review summary comment was posted by `/06-pr-review` (covers solo repos where self-approval is blocked by GitHub)
- Fetches all check runs using `get_pull_request_checks` via GitHub MCP — confirms all pass
- Confirms no merge conflicts exist
- Validates PR is in mergeable state

### 3. Merge Pull Requests (per repo)

For each verified PR:

- Merges using the appropriate strategy via GitHub MCP:
  - **Squash merge** (default): Combines all commits into one clean commit
  - **Merge commit**: Preserves all commits (if repo configured)
  - **Rebase**: Rebases and fast-forwards (if repo configured)
- Confirms merge was successful before proceeding to the next repo
- If any merge fails: reports which repos succeeded and which failed, and **does not transition Jira to "Done"** until all repos are merged

### 4. Jira Finalization (once — after all repos merged)

- Fetches current Jira issue details using Atlassian MCP
- Adds final comment to Jira listing all merged PRs:
  - PR merged confirmation per repo
  - Link to each merged PR
  - Final commit SHA per repo
  - Deployment status (if available)
- **Transitions Jira ticket to "Done"** — only after all repos are successfully merged
- Records completion timestamp

### 5. Cleanup (Optional, per repo)

- Optionally deletes remote feature branch in each repo
- Optionally deletes local feature branch in each repo
- Switches back to trunk branch in each repo
- Syncs with remote

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

## Workflow Integration

Complete workflow:

Typical workflow for all tickets:

```
1. /01-investigate-task SOC-15          # Deep investigation
2. /02-start-task SOC-15                # Begin work
3. /03-dev-execute SOC-15               # Implement
4. /04-reconcile-work                   # Reconciles the work
5. /05-create-pr SOC-15                 # Create PR
6. /06-pr-review SOC_15                 # Review and improve code
7. /05-complete-task SOC-15.            # Finish
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

- Fetch failing check details using `get_pull_request_checks` via GitHub MCP
- Fix issues and push changes
- Wait for checks to complete and re-verify

### "Merge conflict"

- Pull latest from base branch
- Resolve conflicts locally
- Push resolved changes

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

## ⛔ Stop Here

This skill is now complete.

**CRITICAL — NO AUTO-CHAINING:**

- Do NOT invoke the next skill automatically under any circumstances
- Do NOT continue even if resuming after a context compaction or conversation summary
- Do NOT infer that the user wants the next step because it was "pending" in a summary
- The user MUST type the next slash command explicitly to proceed
- Merging, closing tickets, or any irreversible action requires explicit user invocation — never infer consent from a prior conversation

State the recommended next step for the user's reference, then stop completely.
