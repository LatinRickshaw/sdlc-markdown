# sdlc-markdown
A basic software development lifecycle in markdown designed to be executed by AI

## Install into a project

```bash
python3 install.py /path/to/your/project --preset node --dry-run   # preview
python3 install.py /path/to/your/project --preset node             # install
```

This links the skills and the permission hook into the project, merges the permission rules into its `.claude/settings.json`, and adds `.sdlc/` and `.worktrees/` to its `.gitignore` files. Re-run it after changing the rules. Then restart Claude Code in the project and follow "Verify the install".

See [.claude/skills/README.md](.claude/skills/README.md) for the workflow, the full install options, and how to verify the install.
