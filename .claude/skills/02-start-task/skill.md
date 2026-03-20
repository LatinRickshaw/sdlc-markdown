# Start Task Skill

**IMPORTANT: This skill ONLY handles task setup. It does NOT implement the task or write code.**

Automates the workflow for **preparing to begin** a development task:

1. Checks git status to ensure working directory is clean
2. Moves to the `main` branch if not already on the `main` branch locally using git
3. Pulls latest changes from remote (if needed) using git
4. Creates a feature branch for the task uysing git
5. Fetches the Jira ticket details using the Atlassian MCP server
6. Transitions the Jira ticket to "In Progress" using the Atlassian MCP Server
7. Adds a comment to the Jira ticket indicating work has started using the Atlassian MCP Server
8. Analyzes ticket complexity and recommends `/01-investigate-task` if needed (non-blocking)
9. Once complete, it executes the command `say finished starting the task {SOC-XX}`, ensure to replace {SOC-XX} with the actual Jira key.

**After this skill completes, the user should use `/03-dev-execute` to actually implement the task.**

## Usage

```
/02-start-task <JIRA-KEY>
```

### Examples

```bash
# Basic usage
/02-start-task SOC-5

# Start work on a specific ticket
/02-start-task SOC-12
```

## What It Does

### 1. Git Status Check

- Runs `git status` to verify working directory is clean
- If there are uncommitted changes, warns the user and stops
- Ensures you're starting from a clean slate

### 2. Moves to `main`

- Checks if git is already on `main`
- Checks out the `main` branch if not already on `main`

### 3. Sync with Remote (Optional)

- Checks if current branch is behind remote
- If behind, prompts to pull latest changes
- Helps avoid merge conflicts later

### 4. Create Feature Branch

- Creates a feature branch using the naming convention: `feature/<JIRA-KEY>-<description>`
- Example: `feature/SOC-4-platform-templates-optimization`
- Checks out the new branch

### 5. Fetch Jira Ticket using Atlassian MCP Server

- Retrieves the Jira issue details using the Atlassian MCP Server
- Displays the ticket summary and current status
- Confirms the ticket exists before proceeding

### 6. Transition to In Progress using the Atlassian MCP Server

- Fetches available transitions for the ticket using the Atlassian MCP Server
- Looks for "In Progress" transition using the Atlassian MCP Server
- Transitions the ticket from current status (e.g., "To Do") to "In Progress" using the Atlassian MCP Server
- Handles custom workflow transitions automatically

### 7. Add Jira Comment using the Atlassian MCP Server

- Adds a comment to the Jira ticket: "Started work on this task" using the Atlassian MCP Server
- Provides traceability of when work began
- Visible to the team in Jira

### 8. Analyze Complexity & Recommend Investigation (NEW)

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

**Important**: This is a **suggestion only**, not a requirement. The workflow continues regardless of user's decision.

## What It Does NOT Do

**CRITICAL: This skill stops after setup and does NOT:**

- Read or analyze the codebase
- Write any code or implementation
- Create or modify files (except git operations)
- Run tests
- Make commits
- Execute the task requirements

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

- Stop if working directory has uncommitted changes
- Stop if the Atlassian MCP Server stops working
- Report if Jira ticket doesn't exist
- Report if "In Progress" transition is not available
- Provide clear error messages at each step
- Suggest running `/05-complete-task` to commit pending work if needed

## Notes

- Always commit or stash pending work before starting a new task
- Use `git status` to check your working directory before running
- The skill ensures you don't accidentally mix work from multiple tickets
- Pairs well with `/05-complete-task` for a complete workflow
- Jira comments provide audit trail of when work started

## Workflow Integration

**Typical workflow with clear separation of concerns:**

1. **Setup Phase**: `/02-start-task SOC-5`
   - Creates branch `feature/SOC-5-description`
   - Transitions Jira ticket to "In Progress"
   - Adds comment to Jira
   - Analyzes complexity and recommends investigation if needed
   - **STOPS HERE** - Does not implement anything

2. **Optional Investigation Phase**: `/01-investigate-task SOC-5` (if recommended)
   - Only run if complexity indicators detected
   - User can skip if requirements are clear
   - Posts investigation findings to Jira

3. **Implementation Phase**: `/03-dev-execute SOC-5`
   - Fetches requirements from Jira ticket
   - Uses investigation findings if available
   - Analyzes codebase
   - Writes code
   - Runs tests
   - Makes implementation commits

4. **Completion Phase**: `/05-complete-task SOC-5 "Implemented feature X"`
   - Creates final commit
   - Pushes branch
   - Creates pull request
   - Transitions Jira to "Done"

This ensures clean separation between setup, investigation (optional), implementation, and completion phases.

### Example: Simple Task (No Investigation)

```bash
/02-start-task SOC-22
# Output: No complexity indicators detected, proceed directly to implementation
/03-dev-execute SOC-22
```

### Example: Complex Task (Investigation Recommended)

```bash
/02-start-task SOC-14
# Output: ⚠️  COMPLEXITY INDICATORS DETECTED
#         Keywords found: deprecated, migration
#         Consider running: /01-investigate-task SOC-14

# User decides to investigate first
/01-investigate-task SOC-14
# [Investigation findings posted to Jira]

# Then proceed with implementation
/03-dev-execute SOC-14
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
