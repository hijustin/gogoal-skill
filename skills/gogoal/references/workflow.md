# GoGoal Workflow

## Roles and authorization

The user approves goal start, provides external dependencies and decisions, accepts goals, and requests cancellation or archival. The primary AI owns goal analysis, task decomposition, scheduling, implementation review, every lifecycle command, document consistency, and acceptance submission. A sub-agent only produces a candidate implementation and task-level validation for its assigned AI task.

A sub-agent must not run GoGoal mutation commands or edit the four state JSON files, `log.json`, goal/task Markdown, or writing guides. A sub-agent reporting “complete” means only that a candidate result is ready. The primary AI may run `task complete` only after reviewing and integrating it and completing the required validation.

## Goal lifecycle

```text
pending -> active -> review -> completed
             |         |
             v         v
           blocked -> active

pending/active/blocked/review -> cancelled
completed/cancelled -> archived storage
```

- After creating a goal, complete its definition, approach, task plan, and items needing confirmation.
- After the user explicitly approves the current plan, append the plan-start review and then start the goal.
- Before blocking a goal, complete or block every associated `active` AI task. Do not block the whole goal while an executable path remains.
- Submit for review only when all associated tasks are terminal and results and validation are complete.
- When the user requests an in-scope review change, record the review and return the goal to `active`. Out-of-scope work requires a new goal.
- Complete a goal only after explicit user acceptance, and archive it only when the user asks.

## Task lifecycle

AI tasks:

```text
pending -> active -> completed
             |
             v
           blocked -> active

pending/active/blocked -> cancelled
```

User tasks allow only `pending -> completed/cancelled`. Their kind is `dependency`, `decision`, or `other`, and they represent something the user must provide, select, confirm, or handle.

Before starting an AI task, ensure it has a clear boundary, execution plan, completion conditions, and validation plan. The primary AI must also determine that prerequisite AI tasks, user dependencies, shared resources, and required permissions are ready. The current data model has no structured dependency field and the CLI does not parse Markdown, so this semantic gate belongs to the primary AI. A blocker must state its cause, attempted measures, and release condition. After the condition is met, update the document before resuming. Before completion, integrate the result into its intended location and run all required validation.

When creating a goal or AI task or changing a title, the CLI updates structured facts first. The primary AI must immediately create or synchronize the stable-ID Markdown file and run `validate`. Do not run another goal or task mutation during this brief consistency-restoration interval.

## Parallel scheduling

`execution.maxParallelTasks` is the maximum number of active AI tasks; it never requires using sub-agents. The primary AI chooses sequential work, worktrees, sub-agents, or a mixture based on dependencies, file overlap, validation cost, and conflict risk.

Only `active` AI tasks consume capacity; `blocked` tasks do not. Resuming a task may create a temporary non-preemptive excess, but no new task may start while over capacity. The effective limit is exactly one when Git is unavailable, the project is not a repository, `git.enabled=false`, or usable Git worktree isolation is missing.

## Completion and failures

When Git is available and enabled, an AI task is complete only after its result is integrated into the intended target branch and required validation passes against the combined state. When Git is unavailable or disabled, the result must be present in the current project directory and pass required validation there.

On conflicts or test failures, retain the candidate branch/worktree and keep the task `active`. Continue when the issue can be resolved within the task boundary; otherwise record the exception and block the task. Never mark an unintegrated or failing candidate implementation complete.

When management data is inconsistent, stop lifecycle changes, run `validate`, and restore consistency through the CLI from the structured current facts. Do not hand-splice `log.json` and do not replace a whole management file using `ours` or `theirs`.
