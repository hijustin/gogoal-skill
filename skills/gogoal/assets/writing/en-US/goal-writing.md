# Goal document writing guide

Goal documents help the user and AI understand scope, approach, task relationships, delivery, and acceptance. Do not duplicate JSON status or the management log.

Use the following compact structure by default. Internal sections may be adapted, but the Skill's document contract remains mandatory.

```md
# G-<goal-id> <goal-title>

## 1. Goal Definition

State the background, expected outcome, scope, non-goals, deliverables, completion and acceptance expectations, and pre-start questions.

## 2. Implementation Approach

Describe the overall approach, constraints, affected areas, major risks, and permission boundaries.

## 3. Task Plan and Execution

### AI Tasks

| Task | Expected result | Dependencies and order | Execution result summary |
| --- | --- | --- | --- |

### User Tasks

| User task | Kind | Required user action | Result and goal impact |
| --- | --- | --- | --- |

Summarize the current stage, major outcomes, important plan changes, goal-level blockers, and next executable path.

## 4. Delivery and Acceptance

Describe deliverables, verification summary, known limitations, user acceptance items, and the final decision. Write “Not yet occurred” when appropriate.

## 5. Review Record

| Time | Review type | Review content |
| --- | --- | --- |
```

Review records are only for user plan revisions, plan approval, acceptance revisions, acceptance approval, cancellation, or archival. Prefer tables for repeated structured information and Mermaid for complex dependencies or sequences.
