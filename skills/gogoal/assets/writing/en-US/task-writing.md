# AI task document writing guide

Task documents should be compact, executable, and verifiable. Do not duplicate JSON status, timestamps, or the management log. Add internal subsections only when complexity requires them.

```md
# A-<task-id> <task-title>

> Related goal: [G-<goal-id>](../targets/<goal-id>.md)

## 1. Task Definition

State the expected result, scope, non-goals, and dependencies.

## 2. Implementation Plan

Describe steps, impacts on specifications/docs/features/config/tests, risks and recovery, completion conditions, and the verification plan.

## 3. Implementation Record

Record actual changes and important deviations without rewriting the original plan as if no deviation occurred.

## 4. Verification Results

Separate checks or commands, objective results, conclusions, and skipped verification with reasons. Do not paste complete terminal logs.

## 5. Delivery Result

Describe final artifacts, use or integration, known limitations, and branch/worktree cleanup.

## 6. Block, Resume, and Cancellation Record

Record only exceptional causes, attempted measures, recovery conditions, and disposition. Write “None” if no exception occurred.
```

Keep section responsibilities distinct. Prefer tables for repeated structured information and Mermaid for complex relationships.
