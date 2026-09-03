# GoGoal Git, Worktree, and Commit Rules

## Configuration semantics

`git.enabled` controls whether GoGoal uses Git status, branch/worktree assistance, and optional activity queries. It never causes the CLI to commit. `git.autoCommit` only permits the primary AI to create local commits after a complete management action or verified implementation checkpoint. No configuration grants authority to push, open a pull request, publish, or rewrite remote history.

`git.branchPrefix` is the prefix of a complete task branch name. For example, `gogoal/` may produce `gogoal/goal-3-task-8-dashboard`; it is not a directory. `git.worktreeRoot` is the worktree root outside the main repository. The effective path appends a normalized repository name and task name, for example `../.gogoal-worktrees/my-repo/goal-3-task-8-dashboard/`.

When Git is unavailable, the current project is not a Git repository, Git integration is disabled, or `git worktree` is unavailable, do not create isolated branches or worktrees and reduce the effective parallel limit to one. If the worktree root is not writable, stop and ask for a configuration change; do not fall back to a directory inside the repository.

## Execution choice

- Execute sequentially on the current target branch when isolation is unnecessary.
- Create an independent branch and worktree when task boundaries are clear and tasks can run in parallel.
- Give a sub-agent only the context and worktree required for its task. It returns a candidate result, changed files, validation, deviations, limitations, blockers, branch, and commit information.
- The primary AI owns review, integration, combined validation, and lifecycle commands.

Do not create a branch for every task merely for ceremony. Reduce parallelism or execute sequentially for shared core files, migrations, or tasks with high conflict risk.

## Integration gates

1. The candidate task branch worktree is clean and task-level validation passes.
2. The primary AI reviews scope, separation from user changes, and documentation or specification impact.
3. Integrate into the intended target branch. Resolve only conflicts within the current task scope and preserve unrelated user changes.
4. Run required tests against the combined state after integration.
5. Update the task document and run `task complete` only after tests pass.

Parallel or high-risk work should create at most one candidate integration worktree at a time from the latest target branch, named `integrate-goal-<goal>-task-<task>-<slug>`. If the target branch changes in a way that may affect the result during validation, rebuild the candidate on the latest state and rerun affected validation.

When tests fail or conflicts remain unresolved, keep the task `active` and retain its branch and worktree for repair. If work cannot proceed within the task boundary, record the exception before blocking. A candidate branch passing its isolated tests is not enough to complete the task.

When management JSON conflicts, stop the ordinary merge. Do not take the complete `ours` or `theirs` version and do not hand-splice logs. Reapply the necessary management actions through the CLI from the current structured facts.

## Commit boundaries

Recommended commit subjects:

```text
目标-登记-G-3-标题
目标-启动-G-3-标题
AI任务-实现-A-8-标题
AI任务-完成-A-8-标题
用户任务-完成-U-2-标题
```

Use `目标-待验收-G-<id>-<标题>` when submitting a goal for review and `目标-验收修改-G-<id>-<标题>` for requested review changes. The CLI's suggested commit subjects follow the same convention so the dashboard can recognize them when `dashboard.gitActivity` is enabled.

A management commit contains only one complete management action. An implementation commit contains only work inside the task boundary. Do not include unrelated user changes. Task implementation, integration, and task-completion management commits should normally remain independently reviewable. The CLI only returns a suggested subject and never runs `git commit`.

After completion, and only when recovery is no longer needed, safely remove the corresponding worktree and local task branch. Resolve exact paths and branch names and verify there are no uncommitted changes before deletion. Never use broad directories, globs, or destructive resets.
