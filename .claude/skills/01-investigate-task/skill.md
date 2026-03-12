# Investigate Task Skill

Performs deep technical investigation before starting implementation. Use this for complex tasks that may involve deprecated dependencies, architectural decisions, or unclear technical requirements.

## Usage

```
/investigate-task <JIRA-KEY>
```

### Examples

```bash
# Investigate a complex feature
/investigate-task SOC-15

# Investigate before starting
/investigate-task SOC-22
```

## What It Does

This skill performs comprehensive technical investigation and posts findings to Jira WITHOUT transitioning the ticket. Use this BEFORE running `/02-start-task` for complex work. Once complete, it executes the command `say finished investigating the task {SOC-XX}`, ensure to replace {SOC-XX} with the actual Jira key.

### 1. Fetch Ticket Details

- Retrieves Jira ticket with full description using Atlassian MCP server
- Reads all acceptance criteria from the Jira ticket
- Understands scope and requirements
- Identifies deliverables

### 2. Codebase Analysis

Searches the codebase for:

- **Existing implementations** of similar features
- **Deprecated dependencies** that need upgrading
- **Architectural patterns** to follow
- **Related code** that will be affected
- **Test patterns** used in similar features
- **Configuration requirements** (env vars, API keys, etc.)

### 3. Technical Assessment

Evaluates:

- **Complexity level** (simple, moderate, complex)
- **Technology decisions needed**:
  - Which APIs or libraries to use
  - Which architectural patterns to apply
  - Whether refactoring is needed
- **Dependencies or blockers**:
  - Missing infrastructure
  - Deprecated code to upgrade
  - External service requirements
- **Risk factors**:
  - Breaking changes
  - Performance concerns
  - Security considerations

### 4. Scope Clarification

Determines:

- What's explicitly in scope (from the Jira ticket)
- What's implicitly in scope (technical requirements)
- What's out of scope (YAGNI)
- Edge cases to handle
- Edge cases to defer

### 5. Investigation Report

Generates and posts to Jira using the Atlassian MCP server:

```markdown
## 🔍 Technical Investigation Complete

### Ticket Summary

- **What**: [Brief summary of requirement]
- **Why**: [Business value or problem being solved]
- **Acceptance Criteria**: [List key criteria]

### Technical Findings

#### Existing Code Analysis

- Found similar implementation in [file]:line
- Current pattern uses [technology/approach]
- [x] files will likely need modification

#### Deprecated Dependencies

- ⚠️ [Library X] is deprecated, upgrade to [Library Y] recommended
- ⚠️ [Pattern A] no longer follows project standards

#### Architectural Decisions Needed

1. **Decision**: [What needs to be decided]
   - Option A: [Pros/Cons]
   - Option B: [Pros/Cons]
   - Recommendation: [X because Y]

2. **Decision**: [Another decision]
   - [Similar format]

#### Dependencies & Requirements

- Environment variables: [LIST]
- External APIs: [LIST]
- New libraries needed: [LIST]
- Configuration changes: [LIST]

### Complexity Assessment

- **Level**: [Simple/Moderate/Complex]
- **Estimated effort**: [S/M/L/XL]
- **Risk factors**:
  - [List any risks]

### Scope Clarification

#### In Scope (Confirmed)

- [Task A from ticket]
- [Task B from ticket]
- [Technical requirement C]

#### Out of Scope (YAGNI)

- [Feature X not in ticket]
- [Premature optimization Y]

#### Edge Cases

- To Handle: [List cases to implement]
- To Defer: [List cases for future tickets]

### Recommendations

1. [Recommendation 1]
2. [Recommendation 2]
3. [Recommendation 3]

### Proposed Approach

[High-level implementation strategy]

---

Investigation complete. Review findings before running `/start-task [JIRA-KEY]`.
```

### 6. Wait for Review

- **Does NOT transition ticket**
- **Does NOT start implementation**
- Waits for user/team to review findings
- User can then proceed with `/02-start-task` when ready

## When to Use This Skill

### Use for Complex Tasks

- Tasks involving deprecated code
- Tasks requiring architectural decisions
- Tasks with unclear technical requirements
- Tasks affecting multiple systems
- Tasks with performance or security implications
- Large features (L/XL size estimates)

### Skip for Simple Tasks

- Bug fixes with known solution
- Simple UI changes
- Documentation updates
- Configuration changes
- Tasks with clear, simple requirements

## Prerequisites

- Jira MCP server configured in `.mcp.json`
- Git repository initialized
- Access to codebase for analysis

## Arguments

| Argument   | Required | Description                       | Example  |
| ---------- | -------- | --------------------------------- | -------- |
| `jira_key` | Yes      | The Jira issue key to investigate | `SOC-15` |

## Workflow Integration

Typical workflow for complex tasks:

```
1. /01-investigate-task SOC-15          # Deep investigation
2. Review investigation report
3. Discuss architectural decisions
4. /02-start-task SOC-15                # Begin work
5. /03-dev-execute "Feature" SOC-15     # Implement
6. /04-reconcile-work                   # Reconciles the work
7. /05-complete-task SOC-15 "Done"      # Finish
```

For simple tasks:

```
1. /02-start-task SOC-16                # Skip investigation
2. /03-dev-execute "Simple fix" SOC-16
3. /05-complete-task SOC-16 "Done"
```

## Benefits

- **Surfaces technical debt early** - Find deprecated code before starting
- **Prevents mid-work surprises** - No discovering issues halfway through
- **Creates audit trail** - Documents investigation in Jira
- **Enables informed decisions** - Team can review before committing
- **Reduces rework** - Get alignment on approach upfront
- **Better estimates** - Understand complexity before starting

## Error Handling

The skill will:

- Report if Jira ticket doesn't exist
- Continue if some code searches return no results
- Note when architectural decisions are unclear
- Provide partial report if investigation incomplete
- Suggest follow-up questions for user

## Notes

- This is an optional skill - not required for all tasks
- Investigation findings stay in Jira for reference
- User decides when to proceed with implementation
- Can re-run investigation if requirements change
- Helps with sprint planning and estimation
- Particularly valuable for new team members

## Example Output

See the investigation report format above. A real example would include:

- Specific file paths and line numbers
- Actual code patterns found
- Concrete technology recommendations
- Detailed pros/cons for each decision
- Risk assessment with mitigation strategies


---

## ⛔ Stop Here

This skill is now complete. **Do NOT invoke the next skill automatically.**

State what the recommended next step is for the user's reference, then stop and wait for the user to explicitly trigger it.
