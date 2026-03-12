# SDLC Skills Workflow

Comprehensive guide to the 7-skill Software Development Life Cycle (SDLC) workflow for systematic, disciplined software development.

## Overview

This SDLC workflow provides a structured approach to software development with integrated Jira tracking, git operations, and code quality assurance. The workflow consists of 7 skills that guide you from investigation through completion.

**Key Principles:**
- **Jira-first**: All requirements and tracking in Jira
- **Git-centric**: Feature branches, clean commits, pull requests
- **Quality-focused**: Testing, review, and reconciliation built-in
- **Flexible**: Use only the skills you need for each task

---

## The 7 Skills

### 1. `/01-investigate-task` - Deep Technical Investigation

**Purpose**: Investigate complex technical tasks before implementation

**When to Use:**
- Deprecated dependency migrations
- Architectural decisions needed
- Unknown complexity or risks
- Integration with external systems
- Performance or security concerns

**When to Skip:**
- Simple bug fixes
- Well-understood features
- Clear requirements already in Jira
- Obvious implementation approach

**What It Does:**
- Analyzes codebase for patterns
- Identifies multiple approaches
- Documents architectural decisions needed
- Assesses complexity and risks
- Posts investigation report to Jira

**Usage:**
```bash
/01-investigate-task SOC-15
```

**Output**: Investigation report posted as Jira comment

---

### 2. `/02-start-task` - Task Setup & Preparation

**Purpose**: Prepare to begin development work

**When to Use:**
- Starting any new development task
- ALWAYS use this before implementation

**What It Does:**
1. Checks git status (must be clean)
2. Switches to main branch
3. Pulls latest changes
4. Creates feature branch (`feature/SOC-XX-description`)
5. Fetches Jira ticket details
6. Transitions Jira to "In Progress"
7. Adds "Started work" comment to Jira
8. **NEW**: Analyzes complexity and recommends investigation if needed

**Usage:**
```bash
/02-start-task SOC-15
```

**Complexity Analysis (NEW):**
- Detects keywords: deprecated, migration, architecture, refactor, security, etc.
- Suggests `/01-investigate-task` if complexity detected
- Non-blocking recommendation - user decides

**Output**:
- Feature branch created
- Jira ticket in "In Progress"
- Optional investigation recommendation

---

### 3. `/03-dev-execute` - Implementation with Best Practices

**Purpose**: Guide disciplined software development following SOLID, KISS, DRY principles

**When to Use:**
- After `/02-start-task`
- For ANY implementation work
- Bug fixes, features, refactoring

**What It Does:**

**Phase 0: Fetch Task Context (NEW)**
- Fetches ticket from Jira (single source of truth)
- Extracts requirements and acceptance criteria
- Loads any investigation findings

**Phase 1: Understanding & Planning**
- Requirement analysis
- Architecture review
- SOLID design planning
- Test planning
- Architectural Decision Recording (ADR)

**Phase 2: Implementation**
- Step-by-step implementation plan
- Code following SOLID principles
- Silent scope tracking
- Write tests
- Post milestone to Jira

**Phase 3: Verification**
- Self-review checklist
- Run unit tests
- **NEW**: Integration testing (API, CLI, DB, Files, E2E)
- **NEW**: Pre-existing failure handling
- Post tests milestone to Jira

**Phase 4: Documentation & Completion**
- Update documentation
- Prepare scope report
- Generate commit message

**Usage:**
```bash
/03-dev-execute SOC-15
```

**Key Updates (NEW):**
- **Jira-first**: No more manual task description parameter
- **Enhanced ADR**: Two formats (simple and enhanced)
- **Integration testing**: Comprehensive guidance for all integration points
- **Pre-existing failures**: Clear handling strategy

**Output**:
- Implementation complete
- Tests passing
- Documentation updated
- Scope report prepared

---

### 4. `/04-reconcile-work` - Work Audit & Verification

**Purpose**: Verify completed work aligns with ticket requirements

**When to Use:**

**REQUIRED for:**
- Multi-day development (>3 days)
- Multiple commits with scope changes
- Complex tickets with many sub-tasks

**RECOMMENDED for:**
- Work with scope additions/changes
- Want confidence before PR

**SKIP for:**
- Single-commit changes
- Simple bug fixes
- Obvious complete implementations

**Quick Decision Guide:**
```
Multi-day work? ──YES──→ USE
      │
      NO → Scope changes? ──YES──→ USE
                 │
                 NO → Complex? ──YES──→ USE
                           │
                           NO → SKIP
```

**What It Does:**
1. Fetches Jira ticket requirements
2. Analyzes git history on branch
3. Compares work vs requirements
4. Generates reconciliation report
5. Posts summary to Jira
6. Removes temp report file

**Usage:**
```bash
/04-reconcile-work SOC-15
```

**Real-World Example:**
- **SOC-14** (migration): Single commit, clear requirements → ✅ Correctly SKIPPED
- **Complex feature**: Multi-day, scope changes → ⚠️ SHOULD use

**Output**:
- Reconciliation report in Jira
- Alignment score
- Scope divergence analysis
- Recommendations

---

### 5. `/05-create-pr` - Pull Request Creation

**Purpose**: Create pull request and transition Jira

**When to Use:**
- After implementation complete
- Tests passing
- Ready for code review

**What It Does:**
1. Commits all changes
2. Pushes feature branch to remote
3. Creates pull request with generated summary
4. Transitions Jira to "In Review"
5. Posts PR link to Jira

**Usage:**
```bash
/05-create-pr SOC-15 "Implemented JWT authentication"
```

**Output**:
- PR created on GitHub
- Jira in "In Review"
- PR link in Jira comment

---

### 6. `/06-pr-review` - Pull Request Review

**Purpose**: Review and approve pull request

**When to Use:**
- After PR created
- Code review needed

**What It Does:**
1. Fetches PR details
2. Reviews code changes
3. Checks for issues
4. Approves or requests changes

**Usage:**
```bash
/06-pr-review
```

**Output**:
- PR reviewed
- Approval or change requests
- Comments added to PR

---

### 7. `/07-complete-task` - Task Completion

**Purpose**: Merge PR and close ticket

**When to Use:**
- After PR approved
- Ready to merge

**What It Does:**
1. Merges pull request
2. Deletes feature branch
3. Transitions Jira to "Done"
4. Posts completion comment to Jira

**Usage:**
```bash
/07-complete-task
```

**Output**:
- PR merged
- Feature branch deleted
- Jira ticket in "Done"

---

## Complete Workflow Examples

### Example 1: Simple Bug Fix

```bash
# 1. Start task
/02-start-task SOC-22
# Output: No complexity indicators, proceed to implementation

# 2. Implement fix
/03-dev-execute SOC-22
# Output: Bug fixed, tests passing

# 3. Skip reconciliation (simple fix)

# 4. Create PR
/05-create-pr SOC-22 "Fixed race condition in post generation"

# 5. Review
/06-pr-review

# 6. Complete
/07-complete-task
```

**Total Skills Used**: 4 out of 7 (skipped investigation and reconciliation)

---

### Example 2: Complex Feature with Investigation

```bash
# 1. Start task
/02-start-task SOC-14
# Output: ⚠️ COMPLEXITY INDICATORS DETECTED
#         Keywords: deprecated, migration
#         Consider: /01-investigate-task SOC-14

# 2. Investigate first (recommended)
/01-investigate-task SOC-14
# Output: Investigation report posted to Jira

# 3. Implement using investigation findings
/03-dev-execute SOC-14
# Output: Migration complete, tests passing

# 4. Skip reconciliation (single commit, clear scope)

# 5. Create PR
/05-create-pr SOC-14 "Migrated to google-genai SDK"

# 6. Review
/06-pr-review

# 7. Complete
/07-complete-task
```

**Total Skills Used**: 6 out of 7 (skipped reconciliation)

---

### Example 3: Large Feature with Reconciliation

```bash
# 1. Start task
/02-start-task SOC-45
# Output: No complexity indicators

# 2. Implement over several days
/03-dev-execute SOC-45
# Output: Feature complete, 12 commits, scope expanded

# 3. Reconcile work (multi-day, scope changes)
/04-reconcile-work SOC-45
# Output: 90% alignment, scope additions documented

# 4. Create PR
/05-create-pr SOC-45 "Added advanced analytics dashboard"

# 5. Review
/06-pr-review

# 6. Complete
/07-complete-task
```

**Total Skills Used**: 6 out of 7 (skipped investigation)

---

## Skill Selection Decision Trees

### Should I investigate? (`/01-investigate-task`)

```
Does ticket mention:
  - Deprecated dependencies?
  - Architecture decisions?
  - Security/performance concerns?
  - Unknown complexity?
  - External integrations?
    │
    ├─YES──→ /01-investigate-task
    │
    └─NO──→ Skip investigation, proceed to /03-dev-execute
```

### Should I reconcile? (`/04-reconcile-work`)

```
Is it multi-day work (>3 days)? ──YES──→ USE /04-reconcile-work
        │
        NO
        │
        ↓
Were there scope changes? ──YES──→ USE /04-reconcile-work
        │
        NO
        │
        ↓
Is it a complex feature? ──YES──→ USE /04-reconcile-work
        │
        NO
        │
        ↓
More than 3 commits? ──YES──→ CONSIDER /04-reconcile-work
        │
        NO
        │
        ↓
    SKIP (optional)
```

---

## Key Workflow Updates (2026-01-08)

Based on SOC-14 experience and user feedback, the following improvements were made:

### 1. Jira-First Parameters ✅
- **03-dev-execute**: Now takes only `<JIRA-KEY>`, fetches details from Jira
- No more redundant task description parameter
- Single source of truth (Jira)

### 2. Investigation Triggers ✅
- **02-start-task**: Now analyzes ticket complexity
- Detects keywords: deprecated, migration, architecture, refactor, security
- Recommends `/01-investigate-task` when appropriate
- Non-blocking - user maintains control

### 3. Integration Testing Guidance ✅
- **03-dev-execute Phase 3**: Comprehensive integration testing
- Covers: API, CLI, Database, Files, End-to-End
- Clear handling of pre-existing test failures
- Documents integration test results

### 4. Enhanced ADR Template ✅
- **03-dev-execute Phase 1**: Two ADR formats
- Enhanced format: Alternatives, Consequences, Implementation Notes
- Simple format: Still acceptable for straightforward decisions
- Clear guidance on format selection

### 5. Reconciliation Timing Clarity ✅
- **04-reconcile-work**: Decision tree added
- Real-world examples (SOC-14, etc.)
- Clear REQUIRED vs RECOMMENDED vs SKIP criteria
- Quick decision guide flowchart

---

## Best Practices

### 1. Always Start Clean
- Run `/02-start-task` before any development
- Ensure working directory is clean
- Pull latest changes from main

### 2. Use Jira as Source of Truth
- All requirements in Jira tickets
- Investigation reports posted to Jira
- Reconciliation reports posted to Jira
- Milestones commented in Jira

### 3. Follow the Principles
- **SOLID**: Single Responsibility, Open/Closed, Liskov, Interface Segregation, Dependency Inversion
- **KISS**: Keep It Simple, Stupid
- **DRY**: Don't Repeat Yourself (Rule of Three)
- **YAGNI**: You Aren't Gonna Need It

### 4. Document Architectural Decisions
- Use ADR format in code comments
- Choose simple or enhanced format based on complexity
- Place at top of affected files

### 5. Test Thoroughly
- Unit tests for all new code
- Integration tests for all integration points
- Handle pre-existing failures appropriately
- Document test results

### 6. Use Skills Flexibly
- Not every task needs all 7 skills
- Investigation optional (recommended for complex tasks)
- Reconciliation optional (recommended for multi-day work)
- Core workflow: Start → Execute → PR → Review → Complete

---

## Prerequisites

### Required:
- Git repository initialized
- Jira MCP server configured in `.mcp.json`
- Working directory clean (no uncommitted changes)
- Access to Jira tickets

### Optional:
- GitHub CLI (`gh`) for PR creation
- Testing framework (pytest, etc.)
- Code coverage tools

---

## Integration with Tools

### Jira Integration (Atlassian MCP)
- Fetch ticket details
- Transition ticket status
- Post comments
- Track work progress

### Git Integration
- Feature branch creation
- Commit management
- Push to remote
- Branch cleanup

### GitHub Integration
- Pull request creation
- Code review
- PR approval
- Merge operations

---

## Troubleshooting

### "Working directory not clean"
**Solution**: Commit or stash pending changes before `/02-start-task`

### "Jira ticket not found"
**Solution**: Verify ticket key, check Jira access permissions

### "Tests failing"
**Solution**: Check if pre-existing (use git stash to verify) or fix new failures

### "PR creation failed"
**Solution**: Ensure feature branch pushed, verify GitHub CLI configured

### "Investigation recommended but requirements clear"
**Solution**: Skip investigation, proceed directly to `/03-dev-execute`

---

## FAQ

**Q: Do I need to use all 7 skills for every task?**
A: No. Investigation and reconciliation are optional. Core workflow is Start → Execute → PR → Review → Complete.

**Q: When should I investigate?**
A: When `/02-start-task` detects complexity keywords, or for deprecated dependencies, architecture decisions, or unknown complexity.

**Q: When should I reconcile?**
A: For multi-day work (>3 days), multiple commits with scope changes, or complex features. Skip for simple fixes.

**Q: What if investigation is recommended but I skip it?**
A: That's fine. The recommendation is non-blocking. Use your judgment based on requirements clarity.

**Q: Can I use these skills for non-Jira projects?**
A: Skills are Jira-first by design. For non-Jira projects, you'd need to adapt or skip certain steps.

**Q: What happened to task description parameter in `/03-dev-execute`?**
A: Removed in favor of Jira-first approach. Task details now fetched directly from Jira ticket.

---

## Change Log

### 2026-01-08 - Major Workflow Improvements
Based on SOC-14 experience:
- ✅ Made `/03-dev-execute` Jira-first (no task description parameter)
- ✅ Added complexity analysis to `/02-start-task`
- ✅ Added integration testing guidance to `/03-dev-execute`
- ✅ Enhanced ADR template with two formats
- ✅ Added timing decision tree to `/04-reconcile-work`
- ✅ Created comprehensive README

---

## Summary

This SDLC workflow provides a **flexible, disciplined approach** to software development:

- **Investigation (optional)**: Deep analysis for complex tasks
- **Setup (required)**: Git + Jira preparation
- **Execution (required)**: Implementation with best practices
- **Reconciliation (optional)**: Verify alignment with requirements
- **PR Creation (required)**: Create pull request
- **Review (required)**: Code review and approval
- **Completion (required)**: Merge and close

**Use what you need, skip what you don't.** The workflow adapts to your task complexity.

**Philosophy**: Build software that is intentional, simple, focused, tested, secure, maintainable, and extensible.

---

For detailed documentation on each skill, see the individual skill files in this directory.
