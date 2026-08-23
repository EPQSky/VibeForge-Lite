---
name: vibe-init
description: Initialize or migrate a repository for the epq-vibecoding workflow with a dry-run-first, idempotent, conflict-aware process. Use when a project needs Agent guidance, domain docs, tracker conventions, or template upgrades.
---

# Vibe Init

Configure a repository for the installed workflow. This is the only public initialization entry point; do not delegate to or recreate the legacy `setup-matt-pocock-skills` initializer.

The deterministic implementation lives at `scripts/vibe_init.py` inside this skill. Locate this skill directory from the loaded skill path, then use:

```bash
python3 <vibe-init-skill-dir>/scripts/vibe_init.py --target <repo>
python3 <vibe-init-skill-dir>/scripts/vibe_init.py --target <repo> --apply
```

The first command is the default dry-run. Do not use `--apply` until the user has reviewed the plan or explicitly asked to apply a conflict-free initialization.

## Safety Contract

- Inspect first and show a dry-run plan before writing unless the user explicitly asked to apply a previously reviewed plan.
- Never overwrite an existing user-authored file wholesale.
- Maintain generated `AGENTS.md` content inside one versioned managed block:

```md
<!-- epq-vibecoding:start -->
...
<!-- epq-vibecoding:end -->
```

- Preserve content outside the managed block byte-for-byte where practical.
- Record applied template state in `.vibecoding/state.json`.
- Do not delete legacy files, relax sandbox/approval/network policy, or change the issue tracker without confirmation.
- Never write usernames, home directories, workspace-specific absolute paths, credentials, or the source project's domain terms into a reusable project template.

## 1. Inspect

Find the Git root and inspect:

- `AGENTS.md`, `AGENTS.override.md`, `CLAUDE.md`, and nested Agent guidance.
- `.codex/config.toml`, `.agents/skills/`, and legacy `.codex/skills/`.
- `CONTEXT.md`, `CONTEXT-MAP.md`, `docs/adr/`, `docs/agents/`, `.scratch/`, and `.out-of-scope/`.
- Git remotes and existing issue-tracker conventions.
- Absolute paths, old initializer names, missing skill routes, and mixed task states such as `claimed/resolved` versus `ready-for-agent/in-progress/done`.
- `.vibecoding/state.json` to determine fresh install, same-version repeat, or migration.

Treat `CLAUDE.md` as another tool's instructions. Do not modify it unless the user explicitly requests a cross-Agent adapter.

## 2. Resolve Choices

Use these defaults when the repository does not already establish a different convention:

- Local Markdown tracker under `.scratch/`.
- Single domain context: root `CONTEXT.md` plus `docs/adr/`.
- Triage labels: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`.
- Local execution states: `ready-for-agent`, `in-progress`, `done`.
- No project `.codex/config.toml` changes unless a concrete project-scoped Codex setting is needed.
- Plugin-provided skills remain in the Plugin. Do not duplicate them into `.agents/skills/` unless the user explicitly chooses repository vendoring or a project-local override.

Ask only for decisions that inspection cannot determine safely, such as choosing a real issue tracker or adopting an existing conflicting state vocabulary.

## 3. Present Dry Run

Report each proposed action as `create`, `update managed block`, `migrate`, `leave unchanged`, or `conflict`. Include:

- exact target paths;
- why each change is needed;
- content that will be preserved;
- backups or manual resolution required;
- detected legacy paths or project-specific leakage.

Stop after the report when the user requested dry-run only. Otherwise obtain confirmation before applying conflicts or destructive migrations.

Use the script's plan as the filesystem source of truth. Add repository-specific explanation around it, but do not silently implement a second merge algorithm in conversation.

## 4. Apply

The script creates or updates only the selected artifacts:

- `AGENTS.md` managed workflow block;
- `docs/agents/issue-tracker.md`;
- `docs/agents/domain.md`;
- `docs/agents/triage-labels.md` when triage is installed;
- `.scratch/.gitkeep` for a local tracker;
- `docs/adr/.gitkeep` when the directory is intentionally materialized;
- `.vibecoding/state.json`.

Create `CONTEXT.md` lazily only when stable domain vocabulary already exists. Do not seed it with workflow, tool, template, implementation-baseline, or generic software-development terms.

Project `.codex/config.toml` is intentionally not written by the default initializer. When project config is separately requested, use portable settings and never write a user or workspace absolute path.

## 5. Verify

After applying:

1. Run the same inspection again and confirm the plan is now a no-op.
2. Parse JSON, TOML, YAML, and Markdown frontmatter with available structured tools.
3. Confirm every referenced `$skill-name` exists in the installed Plugin or `.agents/skills/`.
4. Scan generated files for absolute paths, source-project names, credentials, legacy `.codex/skills/`, and the old initializer name.
5. Summarize created, updated, unchanged, migrated, and unresolved files.

Do not commit unless the user or applicable repository guidance explicitly requests it.
