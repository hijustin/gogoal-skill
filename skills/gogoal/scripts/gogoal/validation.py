"""配置、结构化数据、文档和日志一致性校验。"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any

from .constants import (
    AI_ACTIONS, AI_STATUSES, ENTITIES, FORMAT_VERSION, GOAL_ACTIONS, GOAL_STATUSES,
    ILLEGAL_CONTROL_RE, SENSITIVE_RE,
    LOCALES, TERMINAL_STATUSES, USER_ACTIONS, USER_KINDS, USER_STATUSES,
)
from .storage import ProjectPaths, safe_document_path

TIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$")

def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _time(value: Any) -> bool:
    if not _text(value) or not TIME_RE.fullmatch(value):
        return False
    try:
        datetime.strptime(value, "%Y-%m-%d %H:%M")
    except ValueError:
        return False
    return True


def _exact_keys(value: dict, expected: set[str], label: str, errors: list[str]) -> None:
    missing = sorted(expected - set(value))
    unknown = sorted(set(value) - expected)
    if missing:
        errors.append(f"{label} 缺少字段：{', '.join(missing)}")
    if unknown:
        errors.append(f"{label} 包含未知字段：{', '.join(unknown)}")


def validate_config(config: Any, root: Path) -> list[str]:
    errors: list[str] = []
    if not isinstance(config, dict):
        return ["config.json 根值必须是对象"]
    _exact_keys(config, {"format", "project", "locale", "execution", "git", "dashboard"}, "config", errors)
    if config.get("format") != FORMAT_VERSION:
        errors.append(f"config.format 必须为 {FORMAT_VERSION}")
    if not _text(config.get("project")):
        errors.append("config.project 必须是非空字符串")
    elif "\n" in config["project"] or "\r" in config["project"] or ILLEGAL_CONTROL_RE.search(config["project"]):
        errors.append("config.project 必须是无控制字符的单行文本")
    elif SENSITIVE_RE.search(config["project"]):
        errors.append("config.project 疑似包含敏感凭据")
    if config.get("locale") not in LOCALES:
        errors.append("config.locale 只允许 zh-CN 或 en-US")
    execution = config.get("execution")
    if not isinstance(execution, dict) or not _is_int(execution.get("maxParallelTasks")) or execution.get("maxParallelTasks", 0) < 1:
        errors.append("config.execution.maxParallelTasks 必须是大于等于 1 的整数")
    else:
        _exact_keys(execution, {"maxParallelTasks"}, "config.execution", errors)
    git = config.get("git")
    if not isinstance(git, dict):
        errors.append("config.git 必须是对象")
    else:
        _exact_keys(git, {"enabled", "autoCommit", "branchPrefix", "worktreeRoot"}, "config.git", errors)
        for key in ("enabled", "autoCommit"):
            if not isinstance(git.get(key), bool):
                errors.append(f"config.git.{key} 必须是布尔值")
        prefix = git.get("branchPrefix")
        unsafe_branch = bool(
            isinstance(prefix, str)
            and (re.search(r"[\s~^:?*\[\\]", prefix) or ".." in prefix or "//" in prefix or "@{" in prefix)
        )
        if not _text(prefix) or not prefix.endswith("/") or prefix.startswith("/") or unsafe_branch:
            errors.append("config.git.branchPrefix 必须是安全的相对前缀并以 / 结尾")
        elif SENSITIVE_RE.search(prefix):
            errors.append("config.git.branchPrefix 疑似包含敏感凭据")
        worktree = git.get("worktreeRoot")
        if not _text(worktree):
            errors.append("config.git.worktreeRoot 必须是非空路径")
        elif "\n" in worktree or "\r" in worktree or ILLEGAL_CONTROL_RE.search(worktree):
            errors.append("config.git.worktreeRoot 不能包含控制字符")
        elif SENSITIVE_RE.search(worktree):
            errors.append("config.git.worktreeRoot 疑似包含敏感凭据")
        else:
            candidate = (root / worktree).resolve() if not Path(worktree).is_absolute() else Path(worktree).resolve()
            try:
                candidate.relative_to(root.resolve())
                errors.append("config.git.worktreeRoot 必须位于项目仓库之外")
            except ValueError:
                pass
    dashboard = config.get("dashboard")
    if not isinstance(dashboard, dict):
        errors.append("config.dashboard 必须是对象")
    else:
        _exact_keys(dashboard, {"host", "port", "refreshSeconds", "autoOpen", "gitActivity"}, "config.dashboard", errors)
        if not _text(dashboard.get("host")):
            errors.append("config.dashboard.host 必须是非空字符串")
        elif "\n" in dashboard["host"] or "\r" in dashboard["host"] or ILLEGAL_CONTROL_RE.search(dashboard["host"]):
            errors.append("config.dashboard.host 必须是无控制字符的单行文本")
        elif SENSITIVE_RE.search(dashboard["host"]):
            errors.append("config.dashboard.host 疑似包含敏感凭据")
        port = dashboard.get("port")
        if not _is_int(port) or not 1 <= port <= 65535:
            errors.append("config.dashboard.port 必须是 1 到 65535 的整数")
        refresh = dashboard.get("refreshSeconds")
        if not _is_int(refresh) or refresh < 1:
            errors.append("config.dashboard.refreshSeconds 必须是大于等于 1 的整数")
        for key in ("autoOpen", "gitActivity"):
            if not isinstance(dashboard.get(key), bool):
                errors.append(f"config.dashboard.{key} 必须是布尔值")
    return errors


def _validate_blocker(record: dict, label: str, errors: list[str]) -> None:
    blocker = record.get("blocker")
    if record.get("status") == "blocked":
        if not isinstance(blocker, dict) or not _text(blocker.get("reason")) or not _text(blocker.get("condition")):
            errors.append(f"{label} blocked 状态必须包含非空 blocker.reason 和 blocker.condition")
        elif set(blocker) != {"reason", "condition"}:
            errors.append(f"{label}.blocker 只允许 reason 和 condition 字段")
        else:
            for field in ("reason", "condition"):
                value = blocker[field]
                if "\n" in value or "\r" in value or ILLEGAL_CONTROL_RE.search(value):
                    errors.append(f"{label}.blocker.{field} 必须是无控制字符的单行文本")
                if SENSITIVE_RE.search(value):
                    errors.append(f"{label}.blocker.{field} 疑似包含敏感凭据")
    elif blocker is not None:
        errors.append(f"{label} 非 blocked 状态的 blocker 必须为 null")


def _validate_terminal(record: dict, archived: bool, label: str, errors: list[str]) -> None:
    terminal = record.get("status") in TERMINAL_STATUSES
    if terminal != _time(record.get("endedAt")):
        errors.append(f"{label} endedAt 必须且仅能在终态为有效本地时间")
    if archived:
        if not terminal or not _time(record.get("archivedAt")):
            errors.append(f"{label} 归档记录必须是终态且包含 archivedAt")
    elif "archivedAt" in record:
        errors.append(f"{label} 活动记录不得包含 archivedAt")


def _validate_common(record: Any, label: str, statuses: tuple[str, ...], archived: bool, errors: list[str]) -> bool:
    if not isinstance(record, dict):
        errors.append(f"{label} 必须是对象")
        return False
    if not _is_int(record.get("id")) or record["id"] < 1:
        errors.append(f"{label}.id 必须是正整数")
    if not _text(record.get("title")):
        errors.append(f"{label}.title 必须是非空字符串")
    elif "\n" in record["title"] or "\r" in record["title"] or ILLEGAL_CONTROL_RE.search(record["title"]):
        errors.append(f"{label}.title 必须是无控制字符的单行文本")
    if not _text(record.get("description")):
        errors.append(f"{label}.description 必须是非空字符串")
    elif ILLEGAL_CONTROL_RE.search(record["description"]):
        errors.append(f"{label}.description 不能包含控制字符")
    for field in ("title", "description"):
        if isinstance(record.get(field), str) and SENSITIVE_RE.search(record[field]):
            errors.append(f"{label}.{field} 疑似包含敏感凭据")
    if record.get("status") not in statuses:
        errors.append(f"{label}.status 非法")
    if not _time(record.get("recordedAt")):
        errors.append(f"{label}.recordedAt 必须是 YYYY-MM-DD HH:mm")
    _validate_terminal(record, archived, label, errors)
    return True


def _validate_document(paths: ProjectPaths, record: dict, entity: str, errors: list[str], warnings: list[str]) -> None:
    expected_rel = f"{'targets' if entity == 'goal' else 'tasks'}/{record.get('id')}.md"
    if record.get("document") != expected_rel:
        errors.append(f"{entity}-{record.get('id')} document 必须为 {expected_rel}")
        return
    try:
        path = safe_document_path(paths, expected_rel)
    except Exception:
        errors.append(f"{entity}-{record.get('id')} 文档路径越界")
        return
    if not path.is_file():
        errors.append(f"缺少对象文档：{expected_rel}")
        return
    try:
        content = path.read_text(encoding="utf-8")
        first = content.splitlines()[0].strip()
    except (OSError, UnicodeError, IndexError):
        errors.append(f"无法读取对象文档一级标题：{expected_rel}")
        return
    prefix = "G" if entity == "goal" else "A"
    expected = f"# {prefix}-{record['id']} {record['title']}"
    if first != expected:
        errors.append(f"{expected_rel} 一级标题必须为：{expected}")
    if SENSITIVE_RE.search(content):
        errors.append(f"{expected_rel} 疑似包含敏感凭据")


def validate_state(
    paths: ProjectPaths,
    state: dict[str, Any],
    strict: bool = False,
    check_documents: bool = True,
) -> dict:
    errors = validate_config(state.get("config.json"), paths.root)
    warnings: list[str] = []
    roots = {
        "target.json": ("targets",),
        "target-archive.json": ("targets",),
        "task.json": ("aiTasks", "userTasks"),
        "task-archive.json": ("aiTasks", "userTasks"),
        "log.json": ("logs",),
    }
    for filename, keys in roots.items():
        value = state.get(filename)
        if not isinstance(value, dict):
            errors.append(f"{filename} 根值必须是对象")
            continue
        _exact_keys(value, set(keys), filename, errors)
        for key in keys:
            if not isinstance(value.get(key), list):
                errors.append(f"{filename}.{key} 必须是数组")
    if errors:
        return {"valid": False, "errors": errors, "warnings": warnings}

    goals: dict[int, dict] = {}
    tasks: dict[tuple[str, int], dict] = {}
    for filename, archived in (("target.json", False), ("target-archive.json", True)):
        for index, goal in enumerate(state[filename]["targets"]):
            label = f"{filename}.targets[{index}]"
            if not _validate_common(goal, label, GOAL_STATUSES, archived, errors):
                continue
            goal_fields = {"id", "title", "description", "status", "document", "recordedAt", "endedAt", "blocker"}
            _exact_keys(goal, goal_fields | ({"archivedAt"} if archived else set()), label, errors)
            _validate_blocker(goal, label, errors)
            identity = goal.get("id")
            if identity in goals:
                errors.append(f"目标编号 {identity} 在活动或归档数据中重复")
            else:
                goals[identity] = goal
            if check_documents:
                _validate_document(paths, goal, "goal", errors, warnings)

    for filename, archived in (("task.json", False), ("task-archive.json", True)):
        for entity, key, statuses in (("ai", "aiTasks", AI_STATUSES), ("user", "userTasks", USER_STATUSES)):
            for index, task in enumerate(state[filename][key]):
                label = f"{filename}.{key}[{index}]"
                if not _validate_common(task, label, statuses, archived, errors):
                    continue
                common_fields = {"id", "title", "description", "status", "goalId", "recordedAt", "endedAt"}
                entity_fields = {"document", "blocker"} if entity == "ai" else {"kind", "result"}
                _exact_keys(task, common_fields | entity_fields | ({"archivedAt"} if archived else set()), label, errors)
                identity = (entity, task.get("id"))
                if identity in tasks:
                    errors.append(f"{entity} 任务编号 {task.get('id')} 在活动或归档数据中重复")
                else:
                    tasks[identity] = task
                if not _is_int(task.get("goalId")) or task.get("goalId") not in goals:
                    errors.append(f"{label}.goalId 必须关联存在的目标")
                if entity == "ai":
                    _validate_blocker(task, label, errors)
                    if check_documents:
                        _validate_document(paths, task, "ai", errors, warnings)
                else:
                    if task.get("kind") not in USER_KINDS:
                        errors.append(f"{label}.kind 非法")
                    terminal = task.get("status") in TERMINAL_STATUSES
                    if terminal and not _text(task.get("result")):
                        errors.append(f"{label} 终态用户任务必须包含非空 result")
                    if not terminal and task.get("result") is not None:
                        errors.append(f"{label} pending 用户任务 result 必须为 null")
                    if isinstance(task.get("result"), str) and SENSITIVE_RE.search(task["result"]):
                        errors.append(f"{label}.result 疑似包含敏感凭据")

                goal = goals.get(task.get("goalId"))
                if goal is not None:
                    goal_archived = "archivedAt" in goal
                    if not archived and goal_archived:
                        errors.append(f"{label} 活动任务不得关联归档目标")
                    if not archived and task.get("status") not in TERMINAL_STATUSES and goal.get("status") not in ("active", "blocked"):
                        errors.append(f"{label} 非终态任务只能关联 active 或 blocked 目标")

    if check_documents:
        for guide in ("goal-writing.md", "task-writing.md"):
            guide_path = paths.file(guide)
            if not guide_path.is_file():
                errors.append(f"缺少项目写作指南：{guide}")
                continue
            try:
                content = guide_path.read_text(encoding="utf-8")
            except (OSError, UnicodeError):
                errors.append(f"无法读取项目写作指南：{guide}")
                continue
            if not content.strip():
                errors.append(f"项目写作指南不能为空：{guide}")
            if SENSITIVE_RE.search(content):
                errors.append(f"项目写作指南疑似包含敏感凭据：{guide}")

    logs = state["log.json"]["logs"]
    seen_log_ids: set[int] = set()
    chains: dict[tuple[str, int], str | None] = {}
    chain_titles: dict[tuple[str, int], str] = {}
    last_id = 0
    actions = {"goal": GOAL_ACTIONS, "ai": AI_ACTIONS, "user": USER_ACTIONS}
    status_sets = {"goal": GOAL_STATUSES, "ai": AI_STATUSES, "user": USER_STATUSES}
    for index, entry in enumerate(logs):
        label = f"log.json.logs[{index}]"
        if not isinstance(entry, dict):
            errors.append(f"{label} 必须是对象")
            continue
        _exact_keys(entry, {"id", "time", "entity", "entityId", "goalId", "title", "action", "statusFrom", "statusTo", "note"}, label, errors)
        log_id = entry.get("id")
        if not _is_int(log_id) or log_id < 1 or log_id in seen_log_ids or log_id <= last_id:
            errors.append(f"{label}.id 必须是递增且不重复的正整数")
        else:
            seen_log_ids.add(log_id)
            last_id = log_id
        entity = entry.get("entity")
        if entity not in ENTITIES:
            errors.append(f"{label}.entity 非法")
            continue
        if entry.get("action") not in actions[entity]:
            errors.append(f"{label}.action 不属于 {entity} 动作枚举")
        if not _time(entry.get("time")) or not _text(entry.get("title")):
            errors.append(f"{label} 时间或标题非法")
        entity_id = entry.get("entityId")
        goal_id = entry.get("goalId")
        if not _is_int(entity_id) or not _is_int(goal_id):
            errors.append(f"{label} entityId 和 goalId 必须是正整数")
            continue
        identity = (entity, entity_id)
        if entity == "goal":
            exists = entity_id in goals and goal_id == entity_id
        else:
            exists = identity in tasks and tasks[identity].get("goalId") == goal_id
        if not exists:
            errors.append(f"{label} 引用了不存在或关联错误的对象")
        before, after = entry.get("statusFrom"), entry.get("statusTo")
        if before is not None and before not in status_sets[entity]:
            errors.append(f"{label}.statusFrom 非法")
        if after is not None and after not in status_sets[entity]:
            errors.append(f"{label}.statusTo 非法")
        if entry.get("action") == "create" and before is not None:
            errors.append(f"{label} create 的 statusFrom 必须为 null")
        previous = chains.get(identity)
        if identity not in chains and entry.get("action") != "create":
            errors.append(f"{label} 是对象首条日志但动作不是 create")
        elif identity in chains and entry.get("action") == "create":
            errors.append(f"{label} 对同一对象重复记录 create")
        if identity in chains and before != previous:
            errors.append(f"{label} 状态链与上一条日志不连续")
        chains[identity] = after
        chain_titles[identity] = entry.get("title")
        if not _valid_log_transition(entity, entry.get("action"), before, after):
            errors.append(f"{label} 动作与状态迁移不匹配")
        if entry.get("note") is not None and not _text(entry.get("note")):
            errors.append(f"{label}.note 必须为 null 或非空字符串")
        elif isinstance(entry.get("note"), str) and ("\n" in entry["note"] or "\r" in entry["note"] or ILLEGAL_CONTROL_RE.search(entry["note"])):
            errors.append(f"{label}.note 必须是无控制字符的单行文本")
        if isinstance(entry.get("note"), str) and SENSITIVE_RE.search(entry["note"]):
            errors.append(f"{label}.note 疑似包含敏感凭据")

    for identity, record in [(('goal', key), value) for key, value in goals.items()] + list(tasks.items()):
        if identity not in chains:
            errors.append(f"{identity[0]}-{identity[1]} 缺少管理日志")
        elif chains[identity] != record.get("status"):
            errors.append(f"{identity[0]}-{identity[1]} 当前状态与日志末状态不一致")
        if identity in chain_titles and chain_titles[identity] != record.get("title"):
            errors.append(f"{identity[0]}-{identity[1]} 当前标题与日志末标题快照不一致")

    active_ai_by_goal: dict[int, list[dict]] = {}
    all_tasks_by_goal: dict[int, list[dict]] = {}
    for (entity, _identity), task in tasks.items():
        all_tasks_by_goal.setdefault(task.get("goalId"), []).append(task)
        if entity == "ai" and "archivedAt" not in task:
            active_ai_by_goal.setdefault(task.get("goalId"), []).append(task)
    for goal_id, goal in goals.items():
        related = all_tasks_by_goal.get(goal_id, [])
        if goal.get("status") == "pending" and related:
            errors.append(f"goal-{goal_id} pending 目标不得包含任务")
        if goal.get("status") == "blocked" and any(task.get("status") == "active" for task in active_ai_by_goal.get(goal_id, [])):
            errors.append(f"goal-{goal_id} blocked 目标不得包含 active AI 任务")
        if goal.get("status") in ("review", "completed", "cancelled") and any(task.get("status") not in TERMINAL_STATUSES for task in related):
            errors.append(f"goal-{goal_id} 当前状态要求全部关联任务为终态")

    if strict and warnings:
        errors.extend(f"严格模式警告：{item}" for item in warnings)
    return {"valid": not errors, "errors": errors, "warnings": warnings}


def _valid_log_transition(entity: str, action: Any, before: Any, after: Any) -> bool:
    if action == "create":
        return before is None and after == "pending"
    if action == "update":
        allowed = ("pending", "active", "blocked", "review") if entity == "goal" else ("pending", "active", "blocked") if entity == "ai" else ("pending",)
        return before == after and before in allowed
    transitions = {
        "goal": {
            "start": ({"pending"}, "active"), "block": ({"active"}, "blocked"),
            "resume": ({"blocked"}, "active"), "submit": ({"active"}, "review"),
            "revise": ({"review"}, "active"), "complete": ({"review"}, "completed"),
            "cancel": ({"pending", "active", "blocked", "review"}, "cancelled"),
            "archive": ({"completed", "cancelled"}, None),
        },
        "ai": {
            "start": ({"pending"}, "active"), "block": ({"active"}, "blocked"),
            "resume": ({"blocked"}, "active"), "complete": ({"active"}, "completed"),
            "cancel": ({"pending", "active", "blocked"}, "cancelled"),
            "archive": ({"completed", "cancelled"}, None),
        },
        "user": {
            "complete": ({"pending"}, "completed"), "cancel": ({"pending"}, "cancelled"),
            "archive": ({"completed", "cancelled"}, None),
        },
    }
    rule = transitions.get(entity, {}).get(action)
    if rule is None:
        return False
    allowed, target = rule
    return before in allowed and after == (before if target is None else target)
