# Start Task Skill

**IMPORTANT: This skill ONLY handles task setup. It does NOT implement the task or write code.**

Automates the workflow for **preparing to begin** a development task:

1. Checks git status to ensure working directory is clean
2. **Discovers all sub git repositories** in the current working directory
3. For each discovered repo: moves to trunk, pulls latest, and creates the feature branch where applicable. Not all tasks require changes in all repos, but this ensures the correct branch structure is in place for any repo that does need changes.
4. Fetches the Jira ticket details using the Atlassian MCP server
5. Transitions the Jira ticket to "In Progress" using the Atlassian MCP Server
6. Adds a comment to the Jira ticket indicating work has started, listing all repos in scope, using the Atlassian MCP Server
7. Once complete, it executes the command `say finished starting the task {SOC-XX}`, ensure to replace {SOC-XX} with the actual Jira key.

**After this skill completes, the user should use `/03-dev-execute` to actually implement the task.**

## Usage

```
/02-start-task <JIRA-KEY>
```

### Examples

```bash
# Basic usage
/02-start-task SOC-5
```

## What It Does

### 1. Git Status Check

- Runs `git status` to verify the current working directory is clean. If the working directory contains multiple sub-dirs as repos, then it checks each one for uncommitted changes.
- If there are uncommitted changes, warns the user and stops
- Ensures you're starting from a clean slate

### 2. Repo Discovery

- Identifies the **current working directory**
- Scans all immediate subdirectories of the **current working directory** for those containing a `.git` folder
- Builds a list of all sibling repos (including the current repo)
- Reports which repos were discovered

> **Note**: All discovered repos are treated as in scope for this ticket. Feature branches will be created in every one of them.

### 3. Branch Setup (per repo)

For **each discovered repo**:

1. Check git status — if the repo has uncommitted changes, **warn the user and STOP!!!**
2. Identify the trunk branch (`main`, `master`, or `trunk` — whichever exists)
3. Checkout the trunk branch
4. Pull latest changes from remote
5. Create and checkout the feature branch: `feature/<JIRA-KEY>-<description>` where applicable.
6. **Trunk protection assertion**: after checkout, verify `git branch --show-current` returns the feature branch name — if it still shows the trunk branch, abort immediately with:
   ```
   ERROR: Failed to switch off trunk branch '<branch>' in <repo>.
   Feature branch creation may have failed. Do not proceed.
   ```

> Example feature branch: `feature/SOC-4-platform-templates-optimization`

### 4. Fetch Jira Ticket using Atlassian MCP Server

- Retrieves the Jira issue details using the Atlassian MCP Server
- Displays the ticket summary and current status
- Confirms the ticket exists before proceeding

### 5. Transition to In Progress using the Atlassian MCP Server

- Fetches available transitions for the ticket using the Atlassian MCP Server
- Looks for "In Progress" transition using the Atlassian MCP Server
- Transitions the ticket from current status (e.g., "To Do") to "In Progress" using the Atlassian MCP Server
- Handles custom workflow transitions automatically

### 6. Add Jira Comment using the Atlassian MCP Server

- Adds a comment to the Jira ticket: "Started work on this task" using the Atlassian MCP Server
- Lists all repos where feature branches were successfully created
- Provides traceability of when work began
- Visible to the team in Jira

### 7. Analyze Complexity & Recommend Investigation

After transitioning the ticket to "In Progress", analyze ticket content for complexity indicators:

**Complexity Keywords Detection:**

Check ticket summary and description for these keywords:

- **Deprecation/Migration**: "deprecated", "migration", "upgrade", "breaking change"
- **Architecture**: "architecture", "refactor", "redesign", "restructure"
- **Performance/Security**: "performance", "security", "scalability", "optimization"
- **Unknown/Research**: "investigate", "research", "unknown", "unclear", "complex"
- **Integration**: "integrate", "external API", "third-party", "service"

**Recommendation Logic:**

If complexity keywords are detected:

1. Display detected keywords to user
2. Show non-blocking recommendation to run `/01-investigate-task`
3. Explain what investigation will provide
4. Clarify that investigation is optional - user can skip if requirements are clear

**When NOT to Suggest:**

Do NOT suggest investigation for tickets with:

- Bug fixes with known solution
- Simple UI changes
- Documentation updates
- Configuration changes
- "simple" or "trivial" labels

**Output Format:**

```
⚠️  COMPLEXITY INDICATORS DETECTED

Keywords found: deprecated, migration, API

RECOMMENDATION:
This task may benefit from technical investigation.

Consider running: /01-investigate-task SOC-XX

Investigation will:
  • Analyze codebase for existing patterns
  • Identify deprecated dependencies
  • Document architectural decisions needed
  • Assess complexity and risks
  • Post findings to Jira for team review

You can skip if requirements are already clear.
```

## What It Does NOT Do

**CRITICAL: This skill stops after setup and does NOT:**

- This skill does not Read or analyze the codebase
- This skill does not Write any code or implementation
- This skill does not Create or modify files (except git operations)
- This skill does not Run tests
- This skill does not Make commits
- This skill does not Execute the task requirements

**The actual implementation work should be done with `/03-dev-execute` after this skill completes.**

## Prerequisites

- Jira MCP server configured in `.mcp.json`
- Git repository initialized
- Git remote configured (optional, for sync check)
- Working directory should be clean (no uncommitted changes)

## Arguments

| Argument   | Required | Description                            | Example |
| ---------- | -------- | -------------------------------------- | ------- |
| `jira_key` | Yes      | The Jira issue key to start working on | `SOC-5` |

## Transition Logic

The skill automatically determines the appropriate Jira transition:

- Looks for transition named "In Progress" (case-insensitive) using the Atlassian MCP Server
- If not found, looks for similar transitions (e.g., "Start Progress", "Begin") using the Atlassian MCP Server
- Reports an error if no suitable transition is found
- Shows current status and available transitions for debugging

## Error Handling

The skill will:

- Stop if the current working directory, or any sub-dir repos has uncommitted changes
- Abort immediately if branch creation leaves any repo on a trunk branch
- Stop if the Atlassian MCP Server stops working
- Report if Jira ticket doesn't exist
- Report if "In Progress" transition is not available
- Provide clear error messages at each step

## Notes

- Use `git status` to check your working directory before running
- The skill ensures you don't accidentally mix work from multiple tickets
- **Never commits directly to trunk** — feature branches are always created first
- Jira comments provide audit trail of when work started and which repos are in scope

## Workflow Integration

Typical workflow for all tickets:

```
1. /01-investigate-task SOC-15          # Deep investigation
2. /02-start-task SOC-15                # Begin work
   2.1. Transition ticket to "In Progress"
   2.2. Create feature branches in all repos
   2.3. Comment on Jira with repos in scope
3. /03-dev-execute SOC-15               # Implement
4. /04-reconcile-work                   # Reconciles the work
5. /05-create-pr SOC-15                 # Create PR
6. /06-pr-review SOC_15                 # Review and improve code
7. /05-complete-task SOC-15.            # Finish
```

### Example: Simple Task (No Investigation)

```bash
/02-start-task SOC-22
```

### Example: Complex Task (Investigation Recommended)

```bash
/02-start-task SOC-14
# Output: ⚠️  COMPLEXITY INDICATORS DETECTED
#         Keywords found: deprecated, migration
#         Consider running: /01-investigate-task SOC-14
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
