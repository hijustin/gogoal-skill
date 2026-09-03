# GoGoal Data and Storage Standard

## Project directory

```text
gogoal/
├── config.json
├── goal-writing.md
├── task-writing.md
├── target.json
├── target-archive.json
├── task.json
├── task-archive.json
├── log.json
├── targets/<goal-id>.md
└── tasks/<ai-task-id>.md
```

The four aggregate JSON files are the structured source of truth for current state. IDs are scanned across active and archived records and are never reused. Goals, AI tasks, and user tasks each have an independent ID sequence.

## Configuration

```json
{
  "format": 1,
  "project": "Project name",
  "locale": "en-US",
  "execution": { "maxParallelTasks": 2 },
  "git": {
    "enabled": true,
    "autoCommit": true,
    "branchPrefix": "gogoal/",
    "worktreeRoot": "../.gogoal-worktrees"
  },
  "dashboard": {
    "host": "127.0.0.1",
    "port": 4173,
    "refreshSeconds": 180,
    "autoOpen": false,
    "gitActivity": true
  }
}
```

- `format`: data-format version; only integer `1` is currently supported.
- `project`: non-empty project name displayed by the dashboard.
- `locale`: exactly `zh-CN` or `en-US`.
- `execution.maxParallelTasks`: configured parallel limit; an integer of at least one.
- `git.enabled`: enables Git capability checks, branch/worktree rules, and optional Git activity. It never causes the CLI to commit.
- `git.autoCommit`: permits the primary AI to create narrowly scoped local commits after complete management actions or verified implementation checkpoints. The CLI never commits.
- `git.branchPrefix`: task-branch prefix, normalized on save to end with `/`.
- `git.worktreeRoot`: root for task worktrees; it must be outside the main repository.
- `dashboard.host` and `dashboard.port`: bind address and port for the read-only HTTP service. The default is loopback-only; explicitly configuring a non-loopback address requires no second confirmation.
- `dashboard.refreshSeconds`: interval for reloading data, at least one second.
- `dashboard.autoOpen`: whether to attempt to open a browser after the service starts.
- `dashboard.gitActivity`: whether to add Git history matching GoGoal commit conventions when Git integration is available.

The configuration object and every nested object allow only the fields listed above. `validate` rejects unknown fields, missing fields, wrong types, and incompatible `format` values. The CLI never guesses or silently migrates data.

## Goals

Both `target.json` and `target-archive.json` contain a root `targets` array. An active goal has these fields:

```json
{
  "id": 1,
  "title": "Build a task management dashboard",
  "description": "Provide a global visual overview",
  "status": "active",
  "document": "targets/1.md",
  "recordedAt": "2026-08-25 10:00",
  "endedAt": null,
  "blocker": null
}
```

Allowed statuses are `pending`, `active`, `blocked`, `review`, `completed`, and `cancelled`. Archived records retain a terminal status and add a non-empty `archivedAt`.

## Tasks

Task files use the root structure `{"aiTasks": [], "userTasks": []}`. An AI task has these fields:

```json
{
  "id": 1,
  "title": "Implement the validator",
  "description": "Validate consistency between data and documents",
  "status": "pending",
  "goalId": 1,
  "document": "tasks/1.md",
  "recordedAt": "2026-08-25 10:10",
  "endedAt": null,
  "blocker": null
}
```

Allowed AI task statuses are `pending`, `active`, `blocked`, `completed`, and `cancelled`. A user task has these fields:

```json
{
  "id": 1,
  "title": "Confirm the license",
  "description": "Choose the open-source license",
  "kind": "decision",
  "status": "pending",
  "result": null,
  "goalId": 1,
  "recordedAt": "2026-08-25 10:15",
  "endedAt": null
}
```

Allowed user task statuses are `pending`, `completed`, and `cancelled`; allowed kinds are `dependency`, `decision`, and `other`. User tasks have no Markdown document. Archived tasks add a non-empty `archivedAt`.

Each record type allows only fields declared by its schema. An active task cannot refer to an archived goal. A non-terminal task can refer only to an `active` or `blocked` goal. A `pending` goal cannot already have tasks; a `blocked` goal cannot retain an `active` AI task; every task associated with a `review`, `completed`, or `cancelled` goal must be terminal.

## Management log

`log.json` contains a root `logs` array. Logs are append-only and have no write API:

```json
{
  "id": 1,
  "time": "2026-08-25 10:00",
  "entity": "goal",
  "entityId": 1,
  "goalId": 1,
  "title": "Build a task management dashboard",
  "action": "create",
  "statusFrom": null,
  "statusTo": "pending",
  "note": null
}
```

`entity` is `goal`, `ai`, or `user`; actions must belong to the command enumeration for that entity. Logs do not record an actor, complete diffs, or before-and-after title fields. Implementation commits belong to Git history and are not written to the management log.

The validator checks every action's allowed source and target states, state-chain continuity, final status, and latest title snapshot. A tampered history must not pass merely because its final status happens to match.

## Invariants and storage

- `blocker` is non-null if and only if status is `blocked`, and then contains non-empty `reason` and `condition` values.
- `endedAt` is non-null if and only if status is `completed` or `cancelled`.
- `archivedAt` exists only on archived records; archived records must be terminal.
- A terminal user task must have a non-empty `result`.
- Every task refers to an existing goal; new tasks can be added only to an active `active` goal.
- Markdown paths must remain under `gogoal/`; filenames and IDs are stable, and the level-one heading must match the JSON ID and current title.
- Timestamps use device-local time in `YYYY-MM-DD HH:mm` form without a timezone or UTC offset, and must represent valid calendar times.
- Mutation commands reread data under one cross-platform file lock, write temporary files, replace atomically, and roll back on ordinary failures. `validate` detects inconsistencies left by extreme failures such as forced process termination.
- Except for the brief interval after creating an object or renaming its title while the AI synchronizes its document, all JSON, logs, guides, and object Markdown must pass full consistency validation inside the lock before a business mutation proceeds. Further transitions are rejected until consistency is restored.
- The CLI verifies written bytes after mutation. Validation fails when JSON, logs, guides, or object Markdown match common credential patterns, but pattern detection never replaces the primary AI's manual security review.
