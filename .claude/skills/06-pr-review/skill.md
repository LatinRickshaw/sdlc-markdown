# Pull Request Review Skill

**Automated PR code review with implementation of improvements and approval.**

This skill conducts comprehensive code review of a pull request, implements recommended improvements, and approves the PR when ready. It does NOT merge the PR - that's handled by `/07-complete-task`.

## Usage

```bash
# Review current branch's PR
/06-pr-review

# Review specific PR
/06-pr-review 42

# Review PR for specific Jira ticket
/06-pr-review SOC-5
```

## What This Skill Does

Once complete, it executes the command `say finished reviewing the pull request for the task {SOC-XX}`, ensure to replace {SOC-XX} with the actual Jira key.

### Phase 1: Fetch PR Details

1. Identifies PR for current branch (or uses specified PR number) using GitHub MCP
2. Fetches PR details: title, description, status, checks
3. Retrieves diff and files changed using GitHub MCP
4. Gets linked Jira ticket details (if available) using Atlassian MCP

### Phase 2: Automated Code Review

Analyzes all touched files comprehensively — not just lines introduced by this PR. The goal is the **highest possible code quality**, so any issue found in a file is in scope regardless of when it was introduced.

- **Critical Issues**: Missing dependencies, breaking changes, security concerns
- **Code Quality**: Type safety, error handling, import organization
- **Documentation**: README updates, docstrings, comments
- **Testing**: Test coverage, edge cases, integration tests
- **Architecture**: Type definitions, code organization, patterns

> **Important**: Do not limit the review to diff lines. If a pre-existing bug, missing test, or quality gap is found anywhere in a touched file, it must be flagged and fixed. The fact that this PR did not introduce the issue is irrelevant — shipping high-quality code is the standard.

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

> **Important**: Fix **all** failing checks and incomplete tasks — regardless of whether this PR caused them. A pre-existing failing check or unchecked task is still a blocker. The bar is a green, shippable PR, not attribution of who broke what.

1. Fetch all PR checks/status using GitHub MCP (`get_pull_request_checks` or `list_check_runs_for_ref`)
2. Fetch all PR tasks/to-do items (checklist items in PR description) using GitHub MCP
3. For each **failed or errored check** (whether introduced by this PR or pre-existing):
   - Identify the root cause by reading the check's log output
   - Fix the underlying issue (e.g. failing tests, lint errors, type errors, build failures)
   - Commit and push the fix
   - Wait for the check to re-run and confirm it passes
4. For each **incomplete PR task** (unchecked checklist item in the PR body, regardless of origin):
   - Determine whether it can be completed programmatically (e.g. "add tests", "update docs")
   - If so, complete the work, commit, and push
   - If it requires human action, flag it explicitly in the PR summary comment
5. Repeat until **all checks are green** and **all automatable tasks are checked off**
6. If a check cannot be fixed after investigation, document the blocker clearly in the PR summary comment and do NOT approve

> **Important**: Do not proceed to Phase 4 (Approval) until all required checks pass and all automatable PR tasks are complete — including any that existed before this PR was opened.

### Phase 4: Approval & Finalization

1. Adds summary comment to PR with completion status using GitHub MCP
2. Approves PR using GitHub MCP — **Note**: GitHub prevents self-approval. If the repository has no external reviewer configured, skip the formal approval and ensure the summary comment (step 1) clearly states the PR is ✅ ready for merge. Do NOT attempt a formal approval that will fail.
3. **Does NOT merge** - merging happens in `/07-complete-task`
4. Reports PR is ready for final review and merge

## Parameters

| Parameter   | Required | Description                               | Example |
| ----------- | -------- | ----------------------------------------- | ------- |
| `pr_number` | No       | PR number (auto-detected if not provided) | `42`    |
| `jira_key`  | No       | Jira ticket key to provide context        | `SOC-5` |

## Workflow Steps

### Step 1: Identify PR

```bash
# Check current branch
git branch --show-current

# Find PR for current branch
gh pr list --head current-branch
```

If PR not found:

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

```bash
# Check PR status/checks
gh pr checks <PR_NUMBER>

# View PR details including task checklist
gh pr view <PR_NUMBER>
```

- Fetch all check runs for the PR's head SHA using GitHub MCP
- For each failing check (whether caused by this PR or pre-existing): read the log, diagnose, fix, push, and wait for re-run
- For each PR task (checklist item in description, regardless of origin): complete automatable ones; flag manual ones
- Repeat until `gh pr checks` shows all checks as passing
- Do NOT advance to Step 5 if any required check is still failing — the cause of the failure is irrelevant

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
/06-pr-review

# Skill fetches PR
Found PR #2 for current branch
Reviewing PR #2: [SOC-4] Implement Platform-Specific Templates

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

## Integration with Other Skills

### Works With:

- `/02-start-task` - Creates feature branch that PR will be based on
- `/03-dev-execute` - Implements features that go into the PR
- `/04-reconcile-work` - Validates work before PR creation
- `/05-create-pr` - Creates the PR that this skill reviews
- `/07-complete-task` - Merges the approved PR

### Typical Workflow:

```bash
1. /02-start-task SOC-5              # Start work
2. /03-dev-execute SOC-5             # Implement feature
3. /04-reconcile-work SOC-5          # Validate completeness
4. /05-create-pr SOC-5 "message"     # Commit and create PR
5. /06-pr-review                     # Review, fix, and approve PR ⬅ THIS SKILL
6. /07-complete-task                 # Merge PR and close Jira
```

## Prerequisites

- GitHub CLI (`gh`) installed and authenticated
- GitHub MCP server configured in `.mcp.json`
- Git repository with remote configured
- PR must already exist (created by `/05-create-pr`)
- Proper branch naming convention (feature/JIRA-KEY-description)

## Configuration

Configure in `.mcp.json`:

```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_..."
      }
    }
  }
}
```

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

- ❌ Does NOT merge the PR (that's `/07-complete-task`)
- ❌ Does NOT transition Jira to "Done" (that's `/07-complete-task`)
- ❌ Does NOT delete branches (that's `/07-complete-task`)
- ❌ Does NOT create the PR (that's `/05-create-pr`)

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
/06-pr-review

Found PR #2 for current branch
Reviewing PR #2: [SOC-4] Implement Platform-Specific Templates

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

### Example 2: Review Specific PR

```bash
# Review a specific PR number
/06-pr-review 45

Reviewing PR #45: [SOC-6] Add Authentication

## Overall Assessment
Good implementation with minor improvements needed.

### Critical Issues (1)
❌ Missing JWT_SECRET environment variable validation
   Files: src/auth/jwt.py
   Fix: Add validation in startup

Implementing fixes...
✓ Fixed critical issue
✓ Added 5 improvements
✓ PR approved

PR is ready for merge.
```

### Example 3: Review with Context

```bash
# Review PR with Jira context
/06-pr-review SOC-6

Found PR #3 for SOC-6
Using Jira context for review...

Reviewing against acceptance criteria:
✓ JWT implementation complete
✓ Refresh token flow working
⚠️ Session management basic

Implementing enhancements...
✓ Improved session management
✓ Added comprehensive tests
✓ PR approved

PR is ready for merge.
```

## Troubleshooting

### Review Doesn't Find Issues

- Ensure PR has actual code changes
- Check file diff is accessible
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

## Difference from Old `/06-pr-workflow`

### Old Behavior:

```
/06-pr-workflow → Create PR → Review → Merge → Close Jira ✅
```

### New Behavior:

```
/05-create-pr → Create PR, Jira → "In Review" 🔍
/06-pr-review → Review and approve PR 🔧 (THIS SKILL)
/07-complete-task → Merge PR, Jira → "Done" ✅
```

**Key improvement**: Clear separation between PR review and PR merge, following standard code review practices where approval happens before merge.

---

**Built to ensure high-quality PRs with comprehensive automated review and improvement**


---

## ⛔ Stop Here

This skill is now complete. **Do NOT invoke the next skill automatically.**

State what the recommended next step is for the user's reference, then stop and wait for the user to explicitly trigger it.
