# Development Execution Skill

Guides the development of software features following engineering best practices including SOLID principles, KISS, DRY, YAGNI and more. This skill ensures code is built correctly from the start, not fixed after the fact.

## Usage

```
/03-dev-execute <JIRA-KEY>
```

### Examples

```bash
# Execute development
/03-dev-execute SOC-15
```

## What It Does

This skill guides you through disciplined software development by completing the following phases. Once complete, it executes the command `say finished executing the task {SOC-XX}`, ensure to replace {SOC-XX} with the actual Jira key.:

## What It Does Not

When writing a commit message, it, in no way, provides any atrribution to Anthropic or Claude Code in the commit message, PR description, or Jira comments. This is a personal commit by the user.

### Phase 0: Fetch Task Context (BEFORE any planning)

**0.1 Retrieve Jira Ticket**

- Fetch ticket using Atlassian MCP server with the provided Jira key
- Extract ticket title and description
- Identify acceptance criteria from ticket
- Check for any investigation report from `/01-investigate-task`
- Retrieve current ticket status
- Use this as the task context throughout all phases

**0.2 Validate Prerequisites**

- Verify ticket exists and is accessible
- Ensure ticket has sufficient detail for implementation
- Note any linked investigation reports or architectural decisions
- Confirm ticket is in "In Progress" status (should be set by `/02-start-task`)

### Phase 1: Understanding & Planning (BEFORE any code)

**1.1 Requirement Analysis**

- What is the actual problem to solve?
- What are the acceptance criteria?
- What are the edge cases?
- What should NOT be built (YAGNI)?

**1.2 Architecture Review**

- Read relevant existing code to understand patterns. There may be multiple repos in the current working directory
- Identify where new code fits in the architecture
- Determine which existing abstractions to use
- Plan how to maintain separation of concerns

**1.3 Design Planning**

- Apply SOLID principles to the design:
  - **Single Responsibility**: What is the ONE thing each class/function does?
  - **Open/Closed**: How can this be extended without modification?
  - **Liskov Substitution**: Are any inheritance hierarchies safe?
  - **Interface Segregation**: What minimal interfaces are needed?
  - **Dependency Inversion**: What abstractions should dependencies use?

- Apply KISS: What's the simplest solution that works?
- Apply DRY: What existing code can be reused?
- Apply YAGNI: What can be left out?

**1.4 Test Planning**

- What unit tests are needed?
- What integration points need testing?
- What edge cases must be covered?
- WHat e2e flows should be tested?

**1.5 Architectural Decision Recording**

- Identify significant architectural decisions needed
- For each major decision, document using one of two formats based on complexity
- Create decision record as code comment in affected files

**Enhanced Format (RECOMMENDED for complex decisions):**

```python
"""
ARCHITECTURAL DECISION: [Short Title]

Context:
[Why this decision was needed - business/technical context]
[What problem does this solve?]

Decision:
[What was chosen - be specific about implementation]

Alternatives Considered:
1. [Option 1]
   - Pros: [Key benefits]
   - Cons: [Key drawbacks]
   - Rejected because: [Specific reason]

2. [Option 2]
   - Pros: [Key benefits]
   - Cons: [Key drawbacks]
   - Rejected because: [Specific reason]

Rationale:
- [Key reason 1 for chosen approach]
- [Key reason 2 for chosen approach]
- [Key reason 3 for chosen approach]

Consequences:
Positive:
  - [Expected benefit 1]
  - [Expected benefit 2]

Negative/Tradeoffs:
  - [Known tradeoff 1]
  - [Known tradeoff 2]

Implementation Notes:
- [Key implementation detail 1]
- [Key implementation detail 2]
- [Any gotchas or maintenance considerations]

Date: YYYY-MM-DD
Ticket: [Jira key]
Author: [Your name or "Claude Sonnet 4.5"]
"""
```

**Simple Format (ACCEPTABLE for straightforward decisions):**

```python
"""
ARCHITECTURAL DECISION: [Short Title]

Context: [Why this decision was needed]
Decision: [What was chosen]
Alternatives: [Other options considered]
Rationale: [Why this choice over alternatives]
Date: YYYY-MM-DD
Ticket: [Jira key]
"""
```

**Guidance on Format Selection:**

Use **Enhanced Format** for:

- Choosing between libraries/frameworks
- Selecting architectural patterns
- Migration from deprecated dependencies
- Performance vs simplicity tradeoffs
- Decisions that affect multiple components
- Decisions with significant long-term impact

Use **Simple Format** for:

- Minor implementation choices
- Obvious technical decisions
- Decisions with limited scope
- Quick tactical choices

**Placement:**

- Place at top of files with significant architectural choices
- Reference decision records in related files if needed
- Keep decision records close to the code they affect

**Examples of Significant Decisions:**

- Choosing between libraries/frameworks
- Selecting architectural patterns (MVC, Repository, etc.)
- Retry/fallback strategies
- Performance vs simplicity tradeoffs
- Migration from deprecated dependencies
- API versioning strategies
- Data persistence approaches
- Error handling philosophies

### Phase 2: Implementation (Writing the code)

**2.1 Create Implementation Plan**
Generate a step-by-step implementation plan:

```markdown
1. Create interfaces/abstractions first (Dependency Inversion)
2. Implement smallest working piece (KISS)
3. Add one responsibility at a time (Single Responsibility)
4. Write tests as you go (TDD when appropriate)
5. Refactor duplication only when it appears (Rule of Three for DRY)
6. Keep classes/functions focused and small
```

**2.2 Scope Tracking (Silent)**

- Track any scope changes made during implementation
- Store the following for completion report:
  - **Within Ticket Scope**: Tasks completed as specified
  - **Beyond Ticket Scope**: Features/enhancements added and why
  - **Deferred from Ticket**: Tasks postponed and why
- Examples of scope additions to track:
  - CLI expanded from "basic" to full featured
  - Added fallback/placeholder systems
  - Additional error handling beyond requirements
  - Performance optimizations not requested
  - Extra validation or security measures

**2.3 Write Code Following Principles**

For each file created/modified:

**SOLID Compliance**

- Each class has ONE clear responsibility
- Each function does ONE thing
- Dependencies are injected, not hardcoded
- Abstractions are used where appropriate
- Interfaces are minimal and focused

**KISS Compliance**

- Use the simplest approach that works
- Avoid premature optimization
- Avoid unnecessary patterns or abstractions
- Prefer clear code over clever code
- Don't build for hypothetical futures

**DRY Compliance**

- Extract duplication after third occurrence (Rule of Three)
- Reuse existing utilities and helpers
- Define constants once
- Share common logic through composition

**Additional Practices**

- Defensive programming at boundaries
- Clear, descriptive naming
- Minimal comments (self-documenting code)
- Proper error handling
- Security considerations (input validation, no injection risks)
- Resource cleanup (context managers, try/finally)

**2.4 Write Tests**

- Unit tests for each new function/class
- Integration tests for component interactions
- Edge case coverage
- Mock external dependencies

**2.5 Milestone Update: Core Implementation**
Post concise Jira comment when core implementation complete:

```markdown
## Milestone: Core Implementation Complete

- X files created, Y files modified
- Z classes/functions added
- Next: Writing tests
```

### Phase 3: Verification (Ensuring quality)

**3.1 Self-Review Checklist**

- [ ] Does each class/function have a single, clear purpose?
- [ ] Can I describe what each part does in one sentence?
- [ ] Are there any YAGNI violations (unused features)?
- [ ] Is the code as simple as possible?
- [ ] Is there any duplication that should be extracted?
- [ ] Are all dependencies injected?
- [ ] Are names clear and descriptive?
- [ ] Are tests written and passing?
- [ ] Are edge cases handled?
- [ ] Are there any security concerns?
- [ ] Would a new developer understand this code easily?

**3.2 Run Unit Tests**

- Execute all new tests
- Run existing test suite to ensure no regressions
- Check code coverage

**3.3 Integration Testing**

Identify and test integration points:

**API Integrations:**

- External API calls (verify with actual endpoints if possible)
- Mock responses for third-party services
- Error handling for network failures
- Timeout and retry mechanisms
- Authentication and authorization flows

**CLI Testing:**

- Run CLI commands with various inputs
- Test help messages and argument parsing
- Verify output formatting
- Test error messages and exit codes
- Test interactive prompts (if applicable)

**Database Integration:**

- Test database connections
- Verify schema changes (if applicable)
- Test data persistence and retrieval
- Test transactions and rollbacks
- Test connection pooling and cleanup

**File I/O:**

- Test file creation, reading, writing
- Verify permissions and error handling
- Test with various file formats
- Test with missing/corrupted files
- Test cleanup of temporary files

**End-to-End Flows:**

- Test complete user workflows
- Verify data flows through system
- Test edge cases and error paths
- Test concurrent operations (if applicable)
- Test with realistic data volumes

**Document Integration Test Results:**

```markdown
Integration Testing Summary:

- CLI tested: [list commands tested]
- API endpoints: [endpoints tested or mocked]
- Database: [operations tested]
- Files: [file operations tested]
- End-to-end: [workflows tested]
- Issues found: [list any issues]
- Resolution: [how issues were resolved]
```

**3.4 Pre-existing Test Failures**

When running test suite:

**If any test failures are found:**

1. MUST fix before proceeding (blocking)
2. Cannot create PR with any failures
3. Debug and resolve all test regressions
4. Re-run full test suite to confirm fix

**3.5 Integration Check**

- Does code integrate cleanly?
- Are existing patterns followed?
- Is the codebase more maintainable than before?

**3.6 Milestone Update: Tests Passing**
Post concise Jira comment when tests complete:

```markdown
## Milestone: All Tests Passing

- X tests written
- Y% coverage achieved
- Z edge cases covered
- Next: Documentation and final review
```

### Phase 4: Documentation & Completion

**4.1 Update Documentation**

- Add docstrings for public APIs
- Update README if needed
- Document any new patterns or decisions
- Add examples if introducing new interfaces

**4.2 Prepare Scope Report**

- Review tracked scope changes from Phase 2
- Format for `/05-complete-task` to include in Jira comment:

  ```markdown
  ## 📊 Scope Changes

  ✅ Within Ticket Scope:

  - Task A: Completed as specified
  - Task B: Completed with minor enhancement

  ⚠️ Beyond Ticket Scope (Added):

  - Feature X: [Brief rationale]
  - Enhancement Y: [Brief rationale]

  🚫 Deferred from Ticket:

  - Task Z: [Reason for deferral]
  ```

- If no scope changes: Note "No scope changes - implemented exactly as specified"

**4.3 Final Commit**

- Always use conventional commit message format
- Include Jira key in commit message
- Summarize changes and principles applied
- Prepare commit with clear message
- Link to Jira ticket if provided
- Include summary of changes and principles applied
- Note number of architectural decisions documented

## Output Format

The skill produces an execution plan and guides implementation:

```markdown
# Development Execution Plan: [Jira Key - Task Title]

## Phase 0: Task Context (from Jira)

### Ticket Information

- **Jira Key**: [Jira key]
- **Title**: [Ticket title]
- **Description**: [Ticket description summary]
- **Status**: [Current status]

### Acceptance Criteria

- [Criterion 1]
- [Criterion 2]
- [...]

### Investigation Report (if available)

- [Link to investigation report in Jira]
- [Key findings from investigation]

## Phase 1: Analysis & Design

### Requirements

- Core requirement: [...]
- Acceptance criteria: [...]
- Edge cases: [...]
- Out of scope (YAGNI): [...]

### Architecture

- Files to create: [...]
- Files to modify: [...]
- Existing patterns to follow: [...]
- Dependencies needed: [...]

### Design

- Classes/Functions needed:
  - `ClassName`: Responsibility - [single clear purpose]
  - `function_name`: Does [one thing]

- SOLID considerations:
  - SRP: [how responsibilities are separated]
  - OCP: [extension points]
  - DIP: [abstractions to use]

- KISS approach: [simplest solution]
- DRY opportunities: [what to reuse]

### Test Plan

- Unit tests: [...]
- Integration tests: [...]
- Edge cases: [...]
- E2E flows: [...]

## Phase 2: Implementation

### Step 1: [First step]

[Code to write]
Principles applied: [...]

### Step 2: [Second step]

[Code to write]
Principles applied: [...]

[Continue for each step...]

## Phase 3: Verification

### Self-Review Results

[Checklist with results]

### Test Results

[Test output and coverage]

## Phase 4: Completion

### Changes Summary

- Files created: [...]
- Files modified: [...]
- Tests added: [...]

### Principles Applied

- SOLID: [how each was applied]
- KISS: [how simplicity was maintained]
- DRY: [what was reused/extracted]
- Security: [considerations addressed]

### Architectural Decisions

- N decisions documented in code comments
- Files with decision records: [list]

### Scope Summary

[Tracked scope changes from Phase 2.2]

### Commit Message

[Generated commit message]
```

## Prerequisites

- Git repository initialized
- Understanding of the task requirements
- Access to existing codebase
- Testing framework available
- Use Atlassian MCP server for Jira integration

## Arguments

| Argument   | Required | Description                     | Example  |
| ---------- | -------- | ------------------------------- | -------- |
| `jira_key` | Yes      | The Jira issue key to implement | `SOC-15` |

## Execution Principles

### Start Simple, Evolve Carefully

1. Build the simplest thing that works first
2. Add complexity only when needed
3. Refactor only when duplication is clear (Rule of Three)
4. Test as you go

### Focus on One Thing at a Time

1. One responsibility per class/function
2. One change per commit (when possible)
3. One level of abstraction per function
4. One reason to change

### Make It Work, Make It Right, Make It Fast

1. **Make it work**: Get functionality working simply
2. **Make it right**: Apply principles, refactor duplication
3. **Make it fast**: Optimize only if needed (measure first)

### Communicate Intent

1. Names should reveal intent
2. Code should read like prose
3. Comments explain WHY, not WHAT
4. Tests document expected behavior

## Examples of Guided Development

### Example 1: Adding a Feature

**Task**: "Add email notification when post is published"

**Phase 1 - Analysis**:

```markdown
Requirements:

- Send email when post status = "published"
- Include post details in email
- Handle email failures gracefully

SOLID Design:

- SRP: Separate EmailService from publishing logic
- DIP: Depend on IEmailService interface, not concrete implementation
- OCP: Allow different notification types to be added

KISS: Just email for now, don't build notification framework
YAGNI: No need for email templates yet, simple text is fine
```

**Phase 2 - Implementation**:

```python
# Step 1: Create interface (DIP)
class IEmailService(Protocol):
    def send_email(self, to: str, subject: str, body: str) -> bool:
        """Send email. Returns True if successful."""
        ...

# Step 2: Implement simple email service (SRP, KISS)
class EmailService:
    def __init__(self, smtp_config: SMTPConfig):
        self.config = smtp_config

    def send_email(self, to: str, subject: str, body: str) -> bool:
        try:
            # Simple implementation using smtplib
            ...
            return True
        except Exception as e:
            logger.error(f"Email failed: {e}")
            return False

# Step 3: Inject into publisher (DIP)
class PostPublisher:
    def __init__(self, email_service: IEmailService):
        self.email_service = email_service

    def publish(self, post: Post) -> None:
        post.status = "published"
        post.save()

        # Notify but don't fail publish if email fails
        self.email_service.send_email(
            to=post.author.email,
            subject=f"Post published: {post.title}",
            body=f"Your post '{post.title}' is now live!"
        )
```

### Example 2: Refactoring

**Task**: "Extract email logic from UserManager (SRP violation)"

**Phase 1 - Analysis**:

```markdown
Current problem:

- UserManager has 3 responsibilities: users, emails, logging
- Violates SRP
- Hard to test
- Hard to reuse email logic

SOLID Design:

- SRP: Create EmailService, LoggingService
- DIP: Inject services into UserManager
- OCP: Services can be swapped/extended

KISS: Just extract services, don't over-engineer
DRY: Consolidate duplicate email code found in 3 places
```

**Phase 2 - Implementation**:

```python
# Step 1: Extract EmailService (existing email code)
class EmailService:
    def send_welcome_email(self, user: User) -> None: ...
    def send_reset_email(self, user: User, token: str) -> None: ...

# Step 2: Simplify UserManager (remove email code)
class UserManager:
    def __init__(self, email_service: EmailService):
        self.email_service = email_service

    def create_user(self, name: str, email: str) -> User:
        user = User(name=name, email=email)
        user.save()
        self.email_service.send_welcome_email(user)  # Delegate
        return user
```

## What This Skill Prevents

- **Big Ball of Mud**: Unstructured code that's hard to maintain
- **God Classes**: Classes that do too much
- **Spaghetti Code**: Tangled dependencies and unclear flow
- **Copy-Paste Programming**: Duplication instead of reuse
- **Premature Optimization**: Complex solutions to simple problems
- **Feature Creep**: Building unnecessary functionality
- **Fragile Code**: Code that breaks when extended
- **Technical Debt**: Shortcuts that cost more later

## Philosophy

Build software that is:

- **Intentional**: Every design choice has a reason
- **Simple**: No unnecessary complexity
- **Focused**: Each part does one thing well
- **Tested**: Verified to work correctly
- **Secure**: Protected by design
- **Maintainable**: Easy for others to understand and change
- **Extensible**: Can grow without breaking

This skill helps you build it right the first time.

## Workflow Integration

Complete workflow:

Typical workflow for all tickets:

```
1. /01-investigate-task SOC-15          # Deep investigation
2. /02-start-task SOC-15                # Begin work
3. /03-dev-execute SOC-15               # Implement
  3.1. Analyze requirements and design
  3.2. Plan implementation steps
  3.3. Write code following principles
  3.4. Write tests
  3.5. Verify implementation and run tests
  3.6. Document architectural decisions and scope changes
  3.7. Prepare commit and Jira comment using conventional commit format
4. /04-reconcile-work                   # Reconciles the work
5. /05-create-pr SOC-15                 # Create PR
6. /06-pr-review SOC_15                 # Review and improve code
7. /05-complete-task SOC-15.            # Finish
```

## Notes

- The skill is a guide, not a rigid process
- Adapt principles to your context
- Simple problems don't need complex solutions
- Sometimes "good enough" is good enough
- Consistency with existing codebase matters
- Ask questions if requirements are unclear
- Iterate and refine as you go
- **Most importantly**: Think before you code

Good software is **designed**, not just **written**.

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
