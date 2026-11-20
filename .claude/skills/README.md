# SDLC Skills Workflow

Comprehensive guide to the 7-skill Software Development Life Cycle (SDLC) workflow for systematic, disciplined software development, plus the `/00-run-sdlc` runner that chains them automatically.

## Overview

This SDLC workflow provides a structured approach to software development with integrated Jira tracking, git operations, and code quality assurance. The workflow consists of 7 skills that guide you from investigation through completion.

**Key Principles:**
- **Jira-first**: All requirements and tracking in Jira
- **Git-centric**: Feature branches, clean commits, pull requests
- **Quality-focused**: Testing, review, and reconciliation built-in
- **Flexible**: Use only the skills you need for each task
- **Automatable**: `/00-run-sdlc` chains the skills with an on-disk state file, stopping before merge by default

---

## The 7 Skills

### 0. `/00-run-sdlc` - Automated Chaining

**Purpose**: Run skills `01` → `07` as one unattended chain for a ticket

**Usage:**
```bash
/00-run-sdlc SOC-15                      # 01 → 06, then stop before merge
/00-run-sdlc SOC-15 --from 02 --until 03 # Any contiguous range
/00-run-sdlc SOC-15 --until 07           # Full run including merge and Jira "Done"
/00-run-sdlc SOC-15 --no-worktree        # Work in-place instead of a worktree
/00-run-sdlc SOC-15 --resume             # Continue a halted pipeline
/00-run-sdlc SOC-15 --status             # Show pipeline state
/00-run-sdlc SOC-15 --reset              # Discard state and start over
```

**Defaults**: `--from 01`, `--until 06`, worktree mode on (`/02-start-task --worktree`). Stage `07` (merge + Done) only runs when you pass `--until 07`.

**How it works:**
1. Preflight: validates args, fetches the Jira ticket, checks the GitHub MCP is available (if `until ≥ 05`), checks the working tree is clean (if `from ≤ 02`)
2. Writes a state file `.sdlc/<JIRA-KEY>.json` (gitignored) with `mode: chained`, the `from`/`until` range, and a status per stage
3. Invokes the first stage. Each stage's closing **"⛔ Stop or Hand Off"** section reads the state file, marks itself `done`, and invokes the next stage, or marks itself `failed` and halts
4. When the stage equal to `until` finishes, the pipeline says it is finished and prints the next manual step

**Halt gates** (the chain stops and keeps the state file for `--resume`):

| Stage | Halts when |
| --- | --- |
| 01 | Ticket not found / Atlassian MCP unavailable |
| 02 | Dirty tree, trunk-protection failure, no "In Progress" transition |
| 03 | Ticket not In Progress, unfixable test failures |
| 04 | Report says **Ready for PR: No** ("With conditions" continues, conditions recorded in `notes`) |
| 05 | On trunk branch, GitHub MCP unavailable, push/PR failure |
| 06 | CI cannot be made green, documented blocker, PR already merged |
| 07 | Any pre-merge check fails, merge fails |

**Safety**: chained mode exists only when the state file says so. A skill invoked by hand with no state file (or a stale one) stops exactly as before. A conversation summary is never treated as evidence that the chain should continue.

---

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

### Example 4: Fully Automated Run

```bash
# One command: investigate → start → execute → reconcile → PR → review
/00-run-sdlc SOC-30
# Output: ... say "finished the SDLC pipeline for SOC-30"
#         Pipeline finished before merge. When you are ready:
#           /07-complete-task SOC-30

# Review the PR yourself, then merge and close
/07-complete-task SOC-30
```

If a stage halts (for example `/04-reconcile-work` reports "Ready for PR: No"):

```bash
# ... say "the SDLC pipeline halted at stage 04 for SOC-30"
# Fix the gap, then:
/00-run-sdlc SOC-30 --resume
```

**Total Skills Used**: all 7, with one manual checkpoint before merge

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

## Install into a project

The skills, the permission hook and the permission rules live in this repo. `install.py` at the repo root wires them into a project. It needs only `python3`.

```bash
# Preview first: prints every change, writes nothing
python3 /path/to/sdlc-markdown/install.py /path/to/your/project --preset node --dry-run

# Install
python3 /path/to/sdlc-markdown/install.py /path/to/your/project --preset node
```

The script does four things:

1. **Links the skills.** Each `.claude/skills/0*` skill is symlinked into the project's `.claude/skills/`, so edits here reach every project at once.
2. **Links the hook.** `.claude/hooks` is symlinked into the project. If the project already has its own `.claude/hooks` folder, only `approve-readonly-bash.py` is linked into it.
3. **Merges the permission rules** from `templates/project-settings.json` into the project's `.claude/settings.json`, plus any `--preset` rules. Commit that file so teammates get the same behaviour.
4. **Updates `.gitignore`** to include `.sdlc/` and `.worktrees/` in the project and in every immediate sub-folder that is a git repo, which covers multi-repo folders.

How the merge treats an existing `settings.json`:

- Missing `allow`, `ask` and `deny` rules are appended. Existing rules are kept as they are, in their original order.
- If one of the template's `ask` rules is also in `allow`, it is removed from `allow`. Those are the force-push and delete rules, and they must always prompt.
- Rules listed under `retired` in the template (or a preset) are removed from `allow`. These are rules an earlier version shipped that the skills no longer use, such as the `gh run …` rules from before the skills went MCP-only. Only exact matches are removed.
- `defaultMode` is set to `acceptEdits` only when the project has no mode yet.
- The PreToolUse Bash hook is registered once.
- Every other key is left untouched.
- The previous file is saved next to it as `settings.json.bak-<timestamp>`. Delete the backup once you are happy with the result.

`settings.local.json` is never touched. Keep personal, machine-specific rules there, and keep branch-specific "don't ask again" entries out of the committed file.

The script is safe to re-run. Run it again after changing the template or a preset to push the new rules out to a project. It only adds rules: a rule you delete from the template must also be deleted from each project by hand.

| Option | Effect |
| --- | --- |
| `--preset NAME` | Also add the tooling rules in `templates/presets/NAME.json`. Repeatable. `node` covers yarn, npx, npm and `docker build`; `react-native` covers read-only `adb` device queries. |
| `--dry-run` | Print what would change and write nothing. |
| `--force` | Repoint skill or hook symlinks that currently point somewhere else. |
| `--no-accept-edits` | Leave `defaultMode` unset, so file edits keep prompting. |

The script never replaces a real file or folder. If the project has its own copy of a skill, or a symlink pointing elsewhere without `--force`, it prints a `CONFLICT` line, carries on with the other steps and exits with code 1. An unreadable `settings.json` is reported the same way and is not overwritten.

To add a preset for another stack, create `templates/presets/<name>.json` with an `allow` list, plus `ask` and `deny` lists if needed, using `node.json` as the model.

Notes:

- File edits stop prompting because of `defaultMode: "acceptEdits"`. The pipeline writes a state file and many source files per run. Git, network and MCP calls follow the permission rules either way.
- The template's MCP rules assume servers named `Atlassian` and `github`, which is how local `.mcp.json` servers are named. A project that uses the claude.ai Atlassian connector instead needs the `mcp__claude_ai_Atlassian_MCP__` prefix in its rules.

### Verify the install

Hooks and settings load only when a session starts, and only from the folder the session starts in. Restart any session that was already open in the project.

**1. Check the hook is registered (terminal).** Start Claude Code from the project root and run `/hooks`:

```bash
cd /path/to/your/project
claude
```

In the `/hooks` menu, pick **PreToolUse**. There should be an entry with matcher **Bash** and this command:

```
python3 -I "${CLAUDE_PROJECT_DIR}/.claude/hooks/approve-readonly-bash.py"
```

If the entry is missing, Claude Code did not read the project's `.claude/settings.json`. The usual causes are a session started from a different folder, or a session that was already running when the settings changed. Also check there are no startup warnings about invalid permission rules.

**2. Check the hook approves read-only commands (terminal or VS Code).** The `/hooks` menu may not be available in the VS Code extension, so this check is the one to use there. Open a new session with the project as the workspace and ask Claude to run:

```bash
cd <sub-repo> && git log -3 --oneline | head -3
```

This shape always prompted before the hook. It should now run without asking. A force push such as `git push --force` must still prompt.

**3. Check a real run.** Run `/01-investigate-task <KEY>` on a ticket. Read-only work should produce no prompts. If something still prompts, start the session with `SDLC_HOOK_DEBUG=1` set, and the hook prints why it did not approve each command.

---

## Shell & Tool Conventions

Every skill carries the same block near its top. The rules exist because Claude Code only auto-approves commands it can prove are read-only, and prompts for anything else:

| Shape | Why it prompts | Use instead |
| --- | --- | --- |
| `cd <repo> && git …` | git after a `cd` into another directory could run that repo's hooks | `git -C <absolute-path> …`, one call per repo |
| `a; b; c` with one non-read-only part | every segment of a compound command must be allowed | split the call, or keep every segment read-only |
| `for r in …; do …; done` | control flow is not analysed | one command per repo per call |
| `python3 -c` / `node -e` | arbitrary code | `jq` |
| `cat <<EOF > file`, `echo > file` | writes through the shell | `Write` / `Edit` tools |
| `curl https://…` | network from the shell | `WebFetch` tool |
| odd quoting, `$(…)`, backticks | unparseable or executes | simple single-line commands |

---

## Permissions

`templates/project-settings.json` has three parts:

- **allow**: read-only commands the built-in set misses (`sed -n`, `jq`, `git show`, `yarn why`, version checks, …), the git workflow the skills perform (`checkout`, `add`, `commit`, `push`, `worktree`, …), the read and comment/transition MCP tools, and the advisory domains for `WebFetch`.
- **ask**: force pushes, `git reset --hard`, `git branch -D`, `git clean`, `rm -r`. An `ask` rule wins over any `allow` rule and over the hook, so these always prompt.
- **hooks**: `.claude/hooks/approve-readonly-bash.py`, a `PreToolUse` hook that re-parses each Bash command and answers "allow" only when every segment is a read-only command from its allow-list, every `cd`/`git -C` path stays inside the project, and nothing can write or execute. It never denies; when unsure it prints nothing and the normal permission flow decides. Set `SDLC_HOOK_DEBUG=1` to trace its decisions on stderr. Known limit: in plan mode the hook cannot approve calls Claude Code itself does not consider read-only, so `cd … && git log` may still prompt there.

Project-specific tooling rules live in `templates/presets/`, and `install.py` merges both into a project. The hook's tests are in `tests/test_readonly_hook.py` and the installer's are in `tests/test_install.py`. Both run with the rest of the suite.

---

## Tests

The skills are markdown, so the test suite checks their structure rather than running them. It verifies the hand-off chain (each stage names the right next skill, `06` guards the merge behind `--until 07`, `07` invokes nothing), the standalone no-chaining wording, the runner defaults, and that every `/NN-skill` reference resolves to a real skill directory.

```bash
python3 -m unittest discover tests
```

## Prerequisites

### Required:
- Git repository initialized
- Jira MCP server configured in `.mcp.json`
- Working directory clean (no uncommitted changes)
- Access to Jira tickets

### Optional:
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

**Q: Does the chain survive a context compaction?**
A: Yes. `/00-run-sdlc` records chained mode and the current stage in `.sdlc/<JIRA-KEY>.json`. After a compaction the stage re-reads that file and re-verifies its own outputs. A summary saying a step was "pending" is never used as a reason to continue.

**Q: Will the chain ever merge my PR without asking?**
A: Only if you pass `--until 07`. The default stops after `/06-pr-review` and tells you to run `/07-complete-task` yourself.

**Q: What if I run a skill by hand while a pipeline state file exists?**
A: The skill only hands off if the file says that exact stage is `in_progress`. Otherwise it prints a stale-file warning and stops as usual. Use `/00-run-sdlc <KEY> --status`, `--resume`, or `--reset` to manage the file.

**Q: Can I use these skills for non-Jira projects?**
A: Skills are Jira-first by design. For non-Jira projects, you'd need to adapt or skip certain steps.

**Q: What happened to task description parameter in `/03-dev-execute`?**
A: Removed in favor of Jira-first approach. Task details now fetched directly from Jira ticket.

---

## Change Log

### 2026-11-17 - Fewer Permission Prompts
- ✅ Added `.claude/hooks/approve-readonly-bash.py`, a PreToolUse hook that auto-approves provably read-only Bash (covers `cd <repo> && git log`, loops, odd quoting) and `tests/test_readonly_hook.py`
- ✅ Added `templates/project-settings.json` with generic allow/ask rules and the hook registration; documented "Install into a project"
- ✅ Added `install.py`, which links the skills and hook, merges the permission rules into a project's `settings.json` with a backup, and updates `.gitignore` in every sub-repo. Re-runnable, with `--dry-run`, `--preset`, `--force` and `--no-accept-edits`
- ✅ Added `templates/presets/node.json` for Node/Yarn tooling rules, and `tests/test_install.py`
- ✅ Added a "Shell & Tool Conventions" block to every skill (`git -C` not `cd && git`, `jq` not inline scripts, `Write`/`Edit` for files, `WebFetch` for advisories)
- ✅ Bounded the state-file search at the project root; state file written and updated with `Write`/`Edit`; reconciliation report moves to the scratchpad
- ✅ Added `__pycache__/` to `.gitignore`

### 2026-11-16 - Automated Chaining
- ✅ Added `/00-run-sdlc` runner with `--from`, `--until`, `--no-worktree`, `--resume`, `--reset`, `--status` (worktree mode is the default)
- ✅ Added `tests/test_skill_contracts.py` to guard the chaining invariants (`python3 -m unittest discover tests`)
- ✅ Replaced each skill's "Stop Here" block with "Stop or Hand Off", driven by `.sdlc/<JIRA-KEY>.json`
- ✅ Default run stops before merge; `--until 07` opts into merge + Jira "Done"
- ✅ Added `.sdlc/` to `.gitignore`
- ✅ Fixed workflow blocks that misnumbered the complete-task step and misspelled the ticket key

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

**Use what you need, skip what you don't.** The workflow adapts to your task complexity. When you want the whole thing run for you, `/00-run-sdlc <KEY>` chains it and stops before merge.

**Philosophy**: Build software that is intentional, simple, focused, tested, secure, maintainable, and extensible.

---

For detailed documentation on each skill, see the individual skill files in this directory.
