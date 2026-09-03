# GoGoal CLI Reference

In this document, `gogoal` means:

```bash
python3.12 <skill-directory>/scripts/gogoal.py
```

Run commands from the project root or any subdirectory. Every query command accepts `--json` for stable JSON output. Mutation commands return affected files and a suggested commit subject, but never create a Git commit. Use the global `--project-root <path>` option to select a project root explicitly.

`config.locale` controls the interface language for CLI help, success messages, error prefixes, statuses, and actions; supported values are `zh-CN` and `en-US`. In `--json` output, field names, status codes, and action codes remain stable. User-authored titles, descriptions, results, and Markdown are never translated. Suggested commit subjects retain the project's Chinese GoGoal convention.

## Initialization, configuration, and validation

| Command | Purpose and usage |
| --- | --- |
| `gogoal init [--project "Name"] [--locale zh-CN\|en-US]` | Create `gogoal/`, default configuration, empty data, logs, detail directories, and writing guides for the selected language. Never overwrite an existing project. |
| `gogoal config list` | List the complete effective configuration. |
| `gogoal config get dashboard.port` | Read one value by dotted path. |
| `gogoal config set dashboard.port 4180` | Set an existing option. Booleans and numbers are parsed as JSON literals; strings are passed directly. |
| `gogoal summary [--archive]` | Summarize goal and task statuses, optionally including archived data. |
| `gogoal validate [--strict]` | Validate configuration, structure, IDs, associations, states, logs, guides, document paths, and level-one headings. Strict mode treats warnings as failures. |

Immediately populate the returned Markdown path after creating an object, and synchronize its level-one heading after renaming. Missing or mismatched documents stop later business mutations until `validate` passes again. User tasks have no Markdown and therefore create no such temporary inconsistency.

## Goal queries and lifecycle

| Command | Purpose and usage |
| --- | --- |
| `gogoal goal list [--status active] [--archive\|--all]` | Query goals. Defaults to non-archived records. |
| `gogoal goal show 1` | Return complete structured data for one goal and whether it is archived. |
| `gogoal goal context 1` | Return compact context for a goal and all associated AI and user tasks. |
| `gogoal goal create --title "Title" --description "Description"` | Register a `pending` goal and allocate a permanent ID and `targets/<id>.md` path. The primary AI then creates its Markdown. |
| `gogoal goal update 1 [--title "New title"] [--description "New description"]` | Update title and/or description. After a title change, the primary AI synchronizes the Markdown heading. |
| `gogoal goal start 1` | Move a goal from `pending` to `active` after the user approves the current plan. |
| `gogoal goal block 1 --reason "Reason" --condition "Release condition"` | Block an `active` goal. Rejected while any associated AI task is `active`. |
| `gogoal goal resume 1` | Remove the blocker and return the goal to `active`. |
| `gogoal goal submit 1` | Move an `active` goal to `review` after every associated task is terminal. |
| `gogoal goal revise 1 --note "Acceptance-change summary"` | Return a goal from `review` to `active` for an in-scope user-requested change. |
| `gogoal goal complete 1` | Complete a goal from `review` after explicit user acceptance. |
| `gogoal goal cancel 1 --reason "Cancellation reason"` | Cancel a goal and consistently cancel every associated non-terminal task. |
| `gogoal goal archive 1` | Archive a terminal goal and its terminal associated tasks that remain active records. Markdown stays in place. |

## Task queries and lifecycle

AI and user tasks have independent IDs, so commands for a single task require `--type ai` or `--type user`.

| Command | Purpose and usage |
| --- | --- |
| `gogoal task list [--goal 1] [--type ai\|user] [--status blocked] [--archive\|--all]` | Query tasks using combined filters. |
| `gogoal task show 2 --type ai` | Query one task. |
| `gogoal task capacity` | Show the configured limit, effective environment limit, active count, remaining slots, blocked count, and Git capability. |
| `gogoal task create --type ai --goal 1 --title "Title" --description "Description"` | Register an AI task for an `active` goal. The primary AI then creates `tasks/<id>.md`. |
| `gogoal task create --type user --kind dependency\|decision\|other --goal 1 --title "Title" --description "Description"` | Register an item the user must provide, decide, or handle. Creates no Markdown. |
| `gogoal task update 2 --type ai\|user [--title "New title"] [--description "New description"]` | Update task information while its state allows changes. |
| `gogoal task start 2 --type ai` | Start an AI task when capacity is available and its goal is `active`. Before calling it, the primary AI must verify that document-declared prerequisites, user dependencies, and shared resources are ready. |
| `gogoal task block 2 --type ai --reason "Reason" --condition "Release condition"` | Block an active AI task and release its parallel slot. |
| `gogoal task resume 2 --type ai` | Resume a blocked task. Temporary non-preemptive excess capacity is allowed. |
| `gogoal task complete 2 --type ai` | Complete a task after the primary AI confirms integration and validation gates. |
| `gogoal task complete 2 --type user --result "User delivery or decision"` | Store a non-empty result and complete a user task. |
| `gogoal task cancel 2 --type ai --reason "Cancellation reason"` | Cancel an AI task. |
| `gogoal task cancel 2 --type user --result "Cancellation reason"` | Store a non-empty reason and cancel a user task. |
| `gogoal task archive 2 --type ai\|user` | Archive a terminal task. |

“Implementation” is not a lifecycle command. It only names meaningful primary-AI implementation commits that have passed their corresponding checks, using `AI任务-实现-A-<id>-<标题>`. It does not change task state or write `log.json`.

## Logs and dashboard

| Command | Purpose and usage |
| --- | --- |
| `gogoal log list [--limit 50] [--goal 1] [--entity goal\|ai\|user] [--id 2] [--action block]` | Query management logs newest first. Defaults to the latest 20. |
| `gogoal log show 15` | Query one complete log record. |
| `gogoal dashboard serve [--host 127.0.0.1] [--port 4180] [--open]` | Start the local read-only dashboard, which reads project data dynamically. Arguments temporarily override this server run without changing configuration. |

The dashboard listens on `127.0.0.1` by default. Explicitly choosing a non-loopback address through configuration or `--host` requires no second confirmation and should be used only on a trusted network.

The CLI offers no command to add, edit, or delete logs; export a static dashboard; create Git commits; push; open pull requests; publish; schedule sub-agents; or generate Markdown bodies.

## Exit codes

- `0`: success.
- `2`: argument, environment, state-transition, data, validation, or security-boundary error.
- `130`: user interruption.
