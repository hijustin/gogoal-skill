---
name: gogoal
description: Manage user-authorized goals from analysis through autonomous execution, task decomposition, user dependencies, validation, acceptance, archival, Git/worktree coordination, and a local read-only dashboard. Use when a user asks to define, start, track, execute, review, resume, cancel, archive, or visualize a goal or its tasks with GoGoal.
---

# GoGoal

Use GoGoal as the management layer for a concrete user goal. Treat the main agent as the only lifecycle owner; delegated agents only produce candidate task implementations.

## Runtime

1. Locate Python 3.12 or newer. Prefer `python3.12`, then a verified `python3`/`python`; on Windows also try `py -3.12`.
2. Invoke `<this-skill>/scripts/gogoal.py` with the compatible interpreter.
3. Run commands from the managed project root. Never directly edit the four state JSON files or `gogoal/log.json`.
4. If `gogoal/config.json` is absent, offer or run `gogoal init` when initialization is within the user's request.
5. Treat this as a portable Agent Skill. Do not require host-specific plugin manifests, marketplaces, package installation, or network downloads.

## Required workflow

1. Analyze the requested result, constraints, risks, deliverables, acceptance expectations, external dependencies, and unresolved decisions.
2. Register a `pending` goal and create its Markdown using the returned stable path. Read `references/document-contract.md` and only `gogoal/goal-writing.md` for this document.
   Do not issue another business mutation until the document exists and `validate` passes.
3. Present the goal definition, implementation approach, and proposed tasks. Do not start until the user explicitly approves the current plan.
4. Record plan approval in the goal document, then run `goal start`.
5. Create tasks only for an `active` goal. Use AI tasks for work the agent can perform; use user tasks only for external dependencies, user decisions, or issues that cannot progress without user action.
   After creating or renaming an AI task, create or synchronize its Markdown and validate before another business mutation.
6. Before starting an AI task, read its goal/task context, `references/document-contract.md`, and `gogoal/task-writing.md`; confirm all predecessor AI tasks, user dependencies, shared resources, and permissions are ready, complete its plan, and query `task capacity`.
7. Choose sequential work, a Git worktree, delegated implementation, or a mixture based on task independence and risk. Respect the effective capacity. Blocked tasks do not consume capacity.
8. Delegated agents must not call GoGoal mutation commands or edit any `gogoal/` management file. Review and integrate their candidate result in the main agent.
9. Complete an AI task only after its result is in the intended integration state and required verification passes. Update its Markdown before the lifecycle command.
10. Submit a goal for review only when all associated tasks are terminal and delivery/verification documentation is complete. Only the user can approve completion.
11. Archive only after the user requests it. Keep Markdown in its stable numbered path.

## Invariants

- JSON is current structured truth; Markdown is detailed context; `log.json` is management history; Git is file history. Do not substitute one for another.
- Never infer authorization to start, accept, cancel, archive, publish, push, or create a pull request.
- Keep status, times, identifiers, and blockers out of Markdown as duplicated truth.
- Use CLI query commands to minimize context; request `--json` only for programmatic processing.
- Run `validate` after a complete management action and before claiming success.
- `git.autoCommit` never makes the CLI commit. It only permits the main agent to create a scoped local commit after the action or implementation is complete and validated.
- When Git integration, repository detection, or Git worktree isolation is unavailable, execute AI tasks sequentially; effective capacity is one.
- Do not store secrets or sensitive production data in GoGoal files or logs.

## Read references on demand

- Read `references/workflow.md` for lifecycle, authorization, delegation, concurrency, recovery, and acceptance rules.
- Read `references/data-format.md` for configuration, schemas, invariants, validation, and storage behavior.
- Read `references/cli-reference.md` before an unfamiliar command or when constructing exact arguments.
- Read `references/document-contract.md` only while creating or updating target/task Markdown.
- Read `references/git-workflow.md` only when Git, branches, worktrees, integration, conflicts, or commits are involved.
