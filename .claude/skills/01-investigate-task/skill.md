# Investigate Task Skill

Performs deep technical investigation before starting implementation. Use this for complex tasks that may involve deprecated dependencies, architectural decisions, or unclear technical requirements.

## Shell & Tool Conventions

These rules keep the skill runnable without permission prompts. Claude Code auto-approves only commands it can prove are read-only, and the project ships a PreToolUse hook that extends that proof; both are defeated by the shapes below.

- Prefer the `Read`, `Grep` and `Glob` tools over Bash `cat`, `grep`, `find` and `sed -n` **if they are listed** in this session; they never prompt inside the project. If `Glob`/`Grep` are not available, fall back to `ls -d */.git` (repo discovery), `ls <dir>`, `grep -n <pattern> <file>` and `git -C <repo> grep -n <pattern>` via Bash; all are auto-approved. Never call a tool that is not listed.
- **Never `cd <dir> && git …`.** Running git after a `cd` into another directory always prompts. Use `git -C <absolute-repo-path> <subcommand>`, one git operation per Bash call.
- No `for`/`while` loops over repos. Run one command per repo per Bash call; parallel calls are fine.
- JSON: `jq` only. Never `python3 -c` or `node -e`; inline scripts are arbitrary code and always prompt.
- No redirects to files except `2>/dev/null`. No `$(…)`, backticks, heredocs, `xargs` with flags, or `find -exec`/`-delete`.
- Files this skill creates (state file, reports) are written with the `Write`/`Edit` tools, never `cat <<EOF >` or `echo >`.
- Temporary reports go in the session scratchpad directory, never in a repo.
- Security advisories and registry metadata via the `WebFetch` tool, never `curl`.
- Keep each command single-line with simple quoting; one job per call.

### Command shapes

Use exactly these shapes; each one matches a shipped permission rule, so any variation prompts. `<repo>` is an absolute repo or worktree path. The yarn flavour of each repo is recorded in the state file (`repos[].yarn`); without a state file, a repo with `.yarnrc.yml` or a `packageManager: "yarn@2+"` field is berry, otherwise classic.

| Action                                   | Shape                                                                                   |
| ---------------------------------------- | --------------------------------------------------------------------------------------- |
| install / build / test (yarn classic)    | `yarn --cwd <repo> install --frozen-lockfile`, `yarn --cwd <repo> build`, `yarn --cwd <repo> test` |
| install / build / test (yarn berry)      | `cd <repo> && corepack yarn install --immutable`, `cd <repo> && corepack yarn build`, `cd <repo> && corepack yarn test` (never `corepack yarn --cwd`: corepack picks the yarn version from the shell cwd) |
| first push of a branch                   | `git -C <repo> push -u origin <branch>`                                                 |
| every later push                         | `git -C <repo> push`                                                                    |
| bring main into the branch               | `git -C <repo> fetch origin main`, then `git -C <repo> merge origin/main --no-edit`     |
| wait for CI                              | GitHub MCP `pull_request_read` with method `get_check_runs`, polled after a background `sleep 90` (Bash `run_in_background`). Never the `gh` CLI. |

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

This skill performs comprehensive technical investigation and posts findings to Jira WITHOUT transitioning the ticket. Use this BEFORE running `/02-start-task` for all tickets. Once complete, it executes the command `say finished investigating the task {SOC-XX}`, ensure to replace {SOC-XX} with the actual Jira key.

### 1. Fetch Ticket Details

- Retrieves Jira ticket with full description using Atlassian MCP server
- Reads all acceptance criteria from the Jira ticket
- Takes into account the existing codebase(s)
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

For dependency and advisory work use `yarn why <pkg>`, `yarn npm audit --json | jq`, `npm view <pkg>`, and the `WebFetch` tool for GitHub advisories and the npm registry. Parse JSON with `jq`, never inline Python or Node.

### 2b. Record Repos (chained mode only)

If a pipeline state file exists (see "Locate the state file" below) and its `repos` is empty, fill it with the `Edit` tool, one entry per repo that is in scope for this ticket:

```json
"repos": [{ "name": "api", "path": "/abs/path/to/api", "yarn": "classic" }]
```

- `path` is the absolute repo path in the main checkout (`/02-start-task` replaces it with the worktree path when it creates one)
- `yarn` is `"berry"` if the repo has `.yarnrc.yml` or `package.json` has `"packageManager": "yarn@2…"` or later (read it with `jq -r .packageManager <repo>/package.json`), `"classic"` if it has a `yarn.lock` otherwise, and `null` for non-yarn repos
- Later stages use these entries instead of rediscovering repos, and pick the install/build/test shape from `yarn`

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
- All tickets

## Prerequisites

- Jira MCP server configured in `.mcp.json`
- Git repository initialized and Github MCP server configured in `.mcp.json`
- Access to codebase for analysis

## Arguments

| Argument   | Required | Description                       | Example  |
| ---------- | -------- | --------------------------------- | -------- |
| `jira_key` | Yes      | The Jira issue key to investigate | `SOC-15` |

## Workflow Integration

Typical workflow for all tickets:

```
0. /00-run-sdlc SOC-15                  # Runs 1–6 below automatically, then stops
1. /01-investigate-task SOC-15          # Deep investigation
  1.2. Review investigation report
  1.3 Discuss architectural decisions
2. /02-start-task SOC-15                # Begin work
3. /03-dev-execute SOC-15               # Implement
4. /04-reconcile-work SOC-15            # Reconciles the work
5. /05-create-pr SOC-15                 # Create PR
6. /06-pr-review SOC-15                 # Review and improve code
7. /07-complete-task SOC-15             # Finish
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

- This is a mandatory step for all tickets, even small ones, to ensure technical due diligence
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

## ⛔ Stop or Hand Off

This skill is now complete. What happens next depends **only** on a pipeline state file on disk, never on conversation history.

### 1. Locate the state file

Look for `.sdlc/<JIRA-KEY>.json` in the current working directory, then in each ancestor directory up to the project root (the directory this Claude session started in), **never above it**. This covers worktrees under `.worktrees/` and multi-repo parent directories. Use the `Read` tool (plus `Glob` if it is listed; otherwise `ls .sdlc/` run from each directory inside the project): looking above the project root prompts and can pick up an unrelated pipeline's file. Use the first file found.

### 2. Standalone mode (no state file, or the file fails validation)

If no file is found, or the file fails any check in step 3, you are in standalone mode. If a file was found but failed validation, first print one line naming the file and the failed check (wrong `jira_key`, `mode` not `chained`, or stage `01` not `in_progress`) so a stale file is noticed. Then:

**CRITICAL — NO AUTO-CHAINING:**

- Do NOT invoke the next skill automatically under any circumstances
- Do NOT continue even if resuming after a context compaction or conversation summary
- Do NOT infer that the user wants the next step because it was "pending" in a summary
- The user MUST type the next slash command explicitly to proceed
- Merging, closing tickets, or any irreversible action requires explicit user invocation — never infer consent from a prior conversation

State the recommended next step for the user's reference, then stop completely.

### 3. Chained mode validation

Chained mode applies only if **all** of the following hold in the file:

- `mode` is `"chained"`
- `jira_key` equals the Jira key this skill was invoked with
- `stages["01"].status` is `"in_progress"`

**Compaction rule**: chained mode is decided by the file on disk and nothing else. Never continue because a summary says the next step was "pending". After any context compaction, re-read the file before acting. If the file says stage `01` is still `in_progress`, re-verify this stage's own outputs (comments posted, branches created, PRs opened, etc.) before marking it done.

### 4. Decide the outcome

This stage **halts** the pipeline if any of these occurred:

- The Jira ticket does not exist or the Atlassian MCP Server is unavailable
- The investigation report could not be posted to Jira

> In chained mode the "Wait for Review" step is skipped: the report is still posted to Jira, but the chain proceeds to `/02-start-task` without waiting.

### 5. Hand off or halt

Update the state file with the `Edit` tool (never a shell redirect) and take timestamps from `date -u +%Y-%m-%dT%H:%M:%SZ`.

**On success:**

1. Set `stages["01"].status = "done"` and `stages["01"].finished_at` in the state file.
2. Then:
   - If `until` equals `"01"`, run the **Finished** announcement from `/00-run-sdlc` ("Pipeline Announcements") and stop.
   - Otherwise, set `stages["02"].status = "in_progress"`, `stages["02"].started_at`, and `current_stage = "02"`, then invoke the next stage via the Skill tool: skill `02-start-task`, args `<JIRA-KEY>` (for `02-start-task`, append `--worktree` when the state file has `"worktree": true`).

**On halt:**

1. Set `stages["01"].status = "failed"` and `halted = { "stage": "01", "reason": "<one line>", "at": "<timestamp>" }`.
2. Run the **Halted** announcement from `/00-run-sdlc` ("Pipeline Announcements").
3. Stop. Do NOT invoke the next stage. The user continues with `/00-run-sdlc <JIRA-KEY> --resume` after fixing the issue.
