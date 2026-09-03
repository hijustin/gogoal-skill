# GoGoal Core Document Contract

This contract overrides project writing guides. A project may customize sections, structure, length, tone, tables, and Mermaid usage, but it cannot remove the semantics required here.

## Source-of-truth boundaries

- Markdown stores detailed context for scope, approach, plans, actual implementation, validation, delivery, reviews, and exceptions.
- JSON stores IDs, titles, descriptions, statuses, timestamps, associations, and current blocker summaries.
- `log.json` stores business-management actions; Git stores actual file diffs.
- Do not duplicate status, recorded time, end time, archive time, or a complete action log in Markdown.
- Do not use Markdown sections or keywords as state-machine input.
- Do not store passwords, keys, tokens, sensitive personal information, or private production data.
- Use only relative paths inside documents; never record machine-specific absolute paths.

Rule priority: platform safety and permission boundaries > this contract > the user's current explicit request > project writing guides > default writing style.

## Goal documents

The level-one heading must be `# G-<id> <title>`. Regardless of layout, every document must express:

1. Goal background, intended outcome, scope, non-goals, deliverables, and completion or acceptance requirements.
2. The confirmed overall approach, constraints, impact, risks, and permission boundaries.
3. AI tasks, user tasks, dependencies or order, execution results, and overall progress.
4. Delivery summary, validation summary, known limitations, acceptance items, and final acceptance result.
5. User lifecycle reviews for plan start, requested acceptance changes, acceptance, cancellation, and archival.

Link AI tasks as `[A-<id>](../tasks/<id>.md)` and refer to user tasks as `U-<id>`. Prefer tables when many items share the same fields. Before starting a goal, resolve every open item that could change the implementation boundary, deliverables, or acceptance requirements.

## AI task documents

The level-one heading must be `# A-<id> <title>` and must link `> Related goal: [G-<goalId>](../targets/<goalId>.md)`. Regardless of layout, every document must express:

1. Intended result, scope, non-goals, and dependencies.
2. Executable plan, impact checks, risks and recovery, completion conditions, and validation plan.
3. Actual changes and meaningful deviations from the plan.
4. Validation performed, objective results, conclusions, and any omitted checks with reasons.
5. Final delivery, usage or integration path, known limitations, and branch/worktree cleanup result.
6. Causes, measures, conditions, and disposition for any block, recovery, or cancellation.

Do not rewrite a plan after the fact to resemble the result. Do not paste complete terminal logs into validation sections. Do not repeat the entire implementation history in delivery. Keep simple tasks compact; add internal subsections only when useful, never to manufacture empty template content.

Do not require the SHA of the commit containing the completed task document itself: that commit does not exist when the document is written, and writing it back would create yet another commit. Record already existing, independent implementation commits, integration commits, or pull requests only when useful.

## Lifecycle synchronization

- Create: immediately create the corresponding Markdown after the CLI allocates an ID, then run `validate`.
- Rename: update JSON through the CLI, then synchronize the level-one heading without changing the path.
- Start: complete the document and record the user's plan approval before running the start command.
- Block, resume, or cancel: write the exception or execution record before running the command.
- Complete a task: integrate, validate, and record implementation, validation, and delivery before completing it.
- Submit for acceptance: complete goal delivery and acceptance material before `goal submit`.
- Revise, accept, cancel, or archive: append the corresponding user review before transitioning.
- Do not rewrite historical facts in a terminal document. Mark corrections explicitly and retain them in Git history.
