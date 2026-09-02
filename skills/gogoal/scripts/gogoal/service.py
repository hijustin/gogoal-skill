"""GoGoal 业务服务、状态机和查询。"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from .constants import (
    AI_STATUSES, EMPTY_FILES, GOAL_STATUSES, ILLEGAL_CONTROL_RE, SENSITIVE_RE, TERMINAL_STATUSES,
    USER_KINDS, USER_STATUSES, new_config,
)
from .errors import GoGoalError, ValidationFailure
from .i18n import system_note
from .platform import git_capability, local_time
from .storage import ProjectPaths, encode_json, load_state, locked, write_many, write_payloads
from .validation import validate_config, validate_state

COMMIT_LABELS = {
    "goal": {
        "create": "登记", "update": "更新", "start": "启动", "block": "阻塞",
        "resume": "恢复", "submit": "待验收", "revise": "验收修改",
        "complete": "完成", "cancel": "取消", "archive": "归档",
    },
    "ai": {
        "create": "登记", "update": "更新", "start": "启动", "block": "阻塞",
        "resume": "恢复", "complete": "完成", "cancel": "取消", "archive": "归档",
    },
    "user": {
        "create": "登记", "update": "更新", "complete": "完成",
        "cancel": "取消", "archive": "归档",
    },
}
COMMIT_ENTITIES = {"goal": "目标", "ai": "AI任务", "user": "用户任务"}


def _required(value: str | None, label: str) -> str:
    if value is None or not value.strip():
        raise GoGoalError(f"{label}不能为空。")
    return value.strip()


def _safe_note(value: str | None, label: str) -> str:
    note = _required(value, label)
    if "\n" in note or "\r" in note or ILLEGAL_CONTROL_RE.search(note):
        raise GoGoalError(f"{label}必须是单行文本且不能包含控制字符。")
    if SENSITIVE_RE.search(note):
        raise GoGoalError(f"{label}疑似包含敏感凭据，拒绝写入管理数据。")
    return note


def _safe_content(value: str | None, label: str) -> str:
    content = _required(value, label)
    if ILLEGAL_CONTROL_RE.search(content):
        raise GoGoalError(f"{label}不能包含控制字符。")
    if SENSITIVE_RE.search(content):
        raise GoGoalError(f"{label}疑似包含敏感凭据，拒绝写入管理数据。")
    return content


def _safe_title(value: str | None) -> str:
    title = _safe_content(value, "标题")
    if "\n" in title or "\r" in title:
        raise GoGoalError("标题必须是单行文本。")
    return title


def _next_id(active: list[dict], archived: list[dict]) -> int:
    ids = [item.get("id", 0) for item in (*active, *archived) if isinstance(item, dict)]
    return max(ids, default=0) + 1


def _find(records: list[dict], identity: int, label: str) -> dict:
    for record in records:
        if record.get("id") == identity:
            return record
    raise GoGoalError(f"未找到{label} {identity}。")


def _append_log(
    state: dict[str, Any], entity: str, record: dict, action: str,
    before: str | None, after: str | None, note: str | None = None,
) -> None:
    logs = state["log.json"]["logs"]
    logs.append({
        "id": max((item.get("id", 0) for item in logs), default=0) + 1,
        "time": local_time(),
        "entity": entity,
        "entityId": record["id"],
        "goalId": record["id"] if entity == "goal" else record["goalId"],
        "title": record["title"],
        "action": action,
        "statusFrom": before,
        "statusTo": after,
        "note": note,
    })


def _validate_for_write(paths: ProjectPaths, state: dict[str, Any]) -> None:
    result = validate_state(paths, state, check_documents=False)
    if not result["valid"]:
        raise ValidationFailure("管理数据不一致：" + "；".join(result["errors"][:5]))


def _validate_current(paths: ProjectPaths, state: dict[str, Any]) -> None:
    result = validate_state(paths, state, check_documents=True)
    if not result["valid"]:
        raise ValidationFailure("现有管理数据或文档不一致，请先修复并运行 validate：" + "；".join(result["errors"][:5]))


def _changed_result(message: str, record: dict | None, files: list[str], commit: str) -> dict:
    result: dict[str, Any] = {
        "message": message,
        "changedFiles": [f"gogoal/{name}" for name in files],
        "suggestedCommit": commit,
    }
    if record is not None:
        result["record"] = copy.deepcopy(record)
    return result


def _suggested_commit(entity: str, action: str, record: dict) -> str:
    prefix = {"goal": "G", "ai": "A", "user": "U"}[entity]
    return f"{COMMIT_ENTITIES[entity]}-{COMMIT_LABELS[entity][action]}-{prefix}-{record['id']}-{record['title']}"


class GoGoalService:
    def __init__(self, paths: ProjectPaths, skill_root: Path) -> None:
        self.paths = paths
        self.skill_root = skill_root

    @classmethod
    def locate(cls, skill_root: Path, start: Path | None = None) -> "GoGoalService":
        return cls(ProjectPaths.locate(start), skill_root)

    @classmethod
    def initialize(
        cls, skill_root: Path, project_root: Path, project: str | None, locale: str,
    ) -> dict:
        paths = ProjectPaths.for_init(project_root)
        if locale not in ("zh-CN", "en-US"):
            raise GoGoalError("locale 只允许 zh-CN 或 en-US。")
        if paths.file("config.json").exists():
            raise GoGoalError("项目已经初始化；重复初始化不会覆盖现有数据或写作指南。")
        managed_files = ("config.json", *EMPTY_FILES.keys(), "goal-writing.md", "task-writing.md")
        conflicts = [name for name in managed_files if paths.file(name).exists()]
        if conflicts:
            raise GoGoalError("检测到未完成初始化留下的管理文件；为避免覆盖，请先人工检查：" + "、".join(conflicts))
        paths.data.mkdir(parents=True, exist_ok=True)
        (paths.data / "targets").mkdir(exist_ok=True)
        (paths.data / "tasks").mkdir(exist_ok=True)
        config = new_config()
        config["project"] = _required(project or project_root.name, "项目名称")
        config["locale"] = locale
        errors = validate_config(config, paths.root)
        if errors:
            raise GoGoalError("初始化配置非法：" + "；".join(errors))
        source = skill_root / "assets" / "writing" / locale
        try:
            payloads = {
                "config.json": encode_json(config),
                **{name: encode_json(value) for name, value in copy.deepcopy(EMPTY_FILES).items()},
                "goal-writing.md": (source / "goal-writing.md").read_bytes(),
                "task-writing.md": (source / "task-writing.md").read_bytes(),
            }
        except OSError as exc:
            raise GoGoalError("Skill 缺少默认写作指南，无法初始化。") from exc
        with locked(paths):
            # 锁内再次检查，避免两个初始化进程同时通过锁前检查。
            conflicts = [name for name in managed_files if paths.file(name).exists()]
            if conflicts:
                raise GoGoalError("初始化期间检测到已存在管理文件，已停止以避免覆盖。")
            write_payloads(paths, payloads)
        return {
            "message": "GoGoal 项目已初始化。",
            "dataDirectory": str(paths.data),
            "changedFiles": [f"gogoal/{name}" for name in ("config.json", *EMPTY_FILES.keys(), "goal-writing.md", "task-writing.md")],
            "suggestedCommit": "配置-初始化-GoGoal",
        }

    def state(self) -> dict[str, Any]:
        return load_state(self.paths)

    def validate(self, strict: bool = False) -> dict:
        return validate_state(self.paths, self.state(), strict=strict)

    def config_list(self) -> dict:
        return copy.deepcopy(self.state()["config.json"])

    def config_get(self, path: str) -> Any:
        value: Any = self.config_list()
        for part in path.split("."):
            if not isinstance(value, dict) or part not in value:
                raise GoGoalError(f"不存在配置项：{path}")
            value = value[part]
        return value

    def config_set(self, path: str, value: Any) -> dict:
        if path == "format":
            raise GoGoalError("format 不能通过 config set 修改。")
        with locked(self.paths):
            state = self.state()
            config = copy.deepcopy(state["config.json"])
            current: Any = config
            parts = path.split(".")
            for part in parts[:-1]:
                if not isinstance(current, dict) or part not in current:
                    raise GoGoalError(f"不存在配置项：{path}")
                current = current[part]
            leaf = parts[-1]
            if not isinstance(current, dict) or leaf not in current:
                raise GoGoalError(f"不存在配置项：{path}")
            if path == "git.branchPrefix" and isinstance(value, str):
                value = value.rstrip("/") + "/"
            current[leaf] = value
            errors = validate_config(config, self.paths.root)
            if errors:
                raise GoGoalError("配置值非法：" + "；".join(errors))
            write_many(self.paths, {"config.json": config})
        return _changed_result(f"已更新配置 {path}。", None, ["config.json"], f"配置-更新-{path}")

    def goal_records(self, mode: str = "active") -> list[dict]:
        state = self.state()
        active = state["target.json"]["targets"]
        archived = state["target-archive.json"]["targets"]
        if mode == "archive":
            return copy.deepcopy(archived)
        if mode == "all":
            return copy.deepcopy([*active, *archived])
        return copy.deepcopy(active)

    def goal_show(self, identity: int) -> dict:
        state = self.state()
        for filename, archived in (("target.json", False), ("target-archive.json", True)):
            for record in state[filename]["targets"]:
                if record.get("id") == identity:
                    result = copy.deepcopy(record)
                    result["archived"] = archived
                    return result
        raise GoGoalError(f"未找到目标 {identity}。")

    def task_records(self, mode: str = "active") -> dict[str, list[dict]]:
        state = self.state()
        if mode == "archive":
            return copy.deepcopy(state["task-archive.json"])
        if mode == "all":
            return {
                "aiTasks": copy.deepcopy([*state["task.json"]["aiTasks"], *state["task-archive.json"]["aiTasks"]]),
                "userTasks": copy.deepcopy([*state["task.json"]["userTasks"], *state["task-archive.json"]["userTasks"]]),
            }
        return copy.deepcopy(state["task.json"])

    def task_show(self, identity: int, entity: str) -> dict:
        key = "aiTasks" if entity == "ai" else "userTasks"
        state = self.state()
        for filename, archived in (("task.json", False), ("task-archive.json", True)):
            for record in state[filename][key]:
                if record.get("id") == identity:
                    result = copy.deepcopy(record)
                    result["archived"] = archived
                    return result
        raise GoGoalError(f"未找到{entity}任务 {identity}。")

    def goal_context(self, identity: int) -> dict:
        goal = self.goal_show(identity)
        tasks = self.task_records("all")
        return {
            "goal": goal,
            "aiTasks": [item for item in tasks["aiTasks"] if item["goalId"] == identity],
            "userTasks": [item for item in tasks["userTasks"] if item["goalId"] == identity],
        }

    def capacity(self) -> dict:
        state = self.state()
        config = state["config.json"]
        git = git_capability(self.paths.root, config["git"]["enabled"])
        enabled = bool(config["git"]["enabled"] and git["available"] and git["repository"])
        parallel_isolation = bool(enabled and git["worktree"])
        configured = config["execution"]["maxParallelTasks"]
        effective = configured if parallel_isolation else 1
        tasks = state["task.json"]["aiTasks"]
        active = sum(item["status"] == "active" for item in tasks)
        blocked = sum(item["status"] == "blocked" for item in tasks)
        return {
            "configuredLimit": configured,
            "effectiveLimit": effective,
            "activeTasks": active,
            "remainingSlots": max(effective - active, 0),
            "blockedTasks": blocked,
            "git": git,
            "gitIntegration": enabled,
            "parallelIsolation": parallel_isolation,
        }

    def summary(self, include_archive: bool = False) -> dict:
        goals = self.goal_records("all" if include_archive else "active")
        tasks = self.task_records("all" if include_archive else "active")

        def counts(records: list[dict], statuses: tuple[str, ...]) -> dict[str, int]:
            result: dict[str, int] = {status: 0 for status in statuses}
            for record in records:
                result[record["status"]] = result.get(record["status"], 0) + 1
            return result

        return {
            "goals": {"total": len(goals), "statuses": counts(goals, GOAL_STATUSES)},
            "aiTasks": {"total": len(tasks["aiTasks"]), "statuses": counts(tasks["aiTasks"], AI_STATUSES)},
            "userTasks": {"total": len(tasks["userTasks"]), "statuses": counts(tasks["userTasks"], USER_STATUSES)},
            "archiveIncluded": include_archive,
            "capacity": self.capacity(),
        }

    def log_list(self) -> list[dict]:
        return copy.deepcopy(self.state()["log.json"]["logs"])

    def log_show(self, identity: int) -> dict:
        return copy.deepcopy(_find(self.state()["log.json"]["logs"], identity, "日志"))

    def goal_create(self, title: str, description: str) -> dict:
        title, description = _safe_title(title), _safe_content(description, "描述")
        with locked(self.paths):
            state = self.state()
            _validate_current(self.paths, state)
            active = state["target.json"]["targets"]
            archived = state["target-archive.json"]["targets"]
            identity = _next_id(active, archived)
            record = {
                "id": identity, "title": title, "description": description,
                "status": "pending", "document": f"targets/{identity}.md",
                "recordedAt": local_time(), "endedAt": None, "blocker": None,
            }
            active.append(record)
            _append_log(state, "goal", record, "create", None, "pending")
            _validate_for_write(self.paths, state)
            write_many(self.paths, {"target.json": state["target.json"], "log.json": state["log.json"]})
        return _changed_result(
            f"已登记目标 G-{identity}；请按写作指南创建 {record['document']}。",
            record, ["target.json", "log.json"], _suggested_commit("goal", "create", record),
        )

    def goal_update(self, identity: int, title: str | None, description: str | None) -> dict:
        if title is None and description is None:
            raise GoGoalError("至少提供 --title 或 --description。")
        with locked(self.paths):
            state = self.state()
            _validate_current(self.paths, state)
            record = _find(state["target.json"]["targets"], identity, "目标")
            if record["status"] in TERMINAL_STATUSES:
                raise GoGoalError("终态或归档目标不能更新。")
            before = record["status"]
            changes: list[str] = []
            if title is not None:
                record["title"] = _safe_title(title)
                changes.append("title")
            if description is not None:
                record["description"] = _safe_content(description, "描述")
                changes.append("description")
            note = system_note(state["config.json"]["locale"], "update", fields=changes)
            _append_log(state, "goal", record, "update", before, before, note)
            _validate_for_write(self.paths, state)
            write_many(self.paths, {"target.json": state["target.json"], "log.json": state["log.json"]})
        return _changed_result(
            f"已更新目标 G-{identity}；标题变化时请同步 Markdown 一级标题。",
            record, ["target.json", "log.json"], _suggested_commit("goal", "update", record),
        )

    def _goal_transition(
        self, identity: int, action: str, allowed: tuple[str, ...], target: str,
        note: str | None = None, blocker: dict | None = None,
    ) -> dict:
        with locked(self.paths):
            state = self.state()
            _validate_current(self.paths, state)
            record = _find(state["target.json"]["targets"], identity, "目标")
            before = record["status"]
            if before not in allowed:
                raise GoGoalError(f"目标 G-{identity} 不能从 {before} 执行 {action}。")
            tasks = [
                item for item in state["task.json"]["aiTasks"]
                if item["goalId"] == identity
            ]
            if action == "block" and any(item["status"] == "active" for item in tasks):
                raise GoGoalError("目标阻塞前必须先完成或阻塞全部 active AI 任务。")
            if action == "submit":
                all_tasks = [
                    item for filename in ("task.json", "task-archive.json")
                    for key in ("aiTasks", "userTasks")
                    for item in state[filename][key] if item["goalId"] == identity
                ]
                if any(item["status"] not in TERMINAL_STATUSES for item in all_tasks):
                    raise GoGoalError("仍有关联任务不是终态，不能提交目标验收。")
            record["status"] = target
            record["blocker"] = blocker
            if target in TERMINAL_STATUSES:
                record["endedAt"] = local_time()
            else:
                record["endedAt"] = None
            _append_log(state, "goal", record, action, before, target, note)
            _validate_for_write(self.paths, state)
            write_many(self.paths, {"target.json": state["target.json"], "log.json": state["log.json"]})
        return _changed_result(
            f"目标 G-{identity} 已执行 {action}，当前状态为 {target}。",
            record, ["target.json", "log.json"], _suggested_commit("goal", action, record),
        )

    def goal_start(self, identity: int) -> dict:
        return self._goal_transition(identity, "start", ("pending",), "active")

    def goal_block(self, identity: int, reason: str, condition: str) -> dict:
        reason, condition = _safe_note(reason, "阻塞原因"), _safe_note(condition, "解除条件")
        note = system_note(self.config_get("locale"), "block", reason=reason, condition=condition)
        return self._goal_transition(
            identity, "block", ("active",), "blocked",
            note, {"reason": reason, "condition": condition},
        )

    def goal_resume(self, identity: int) -> dict:
        return self._goal_transition(identity, "resume", ("blocked",), "active", system_note(self.config_get("locale"), "resume"))

    def goal_submit(self, identity: int) -> dict:
        return self._goal_transition(identity, "submit", ("active",), "review")

    def goal_revise(self, identity: int, note: str) -> dict:
        return self._goal_transition(identity, "revise", ("review",), "active", _safe_note(note, "验收修改摘要"))

    def goal_complete(self, identity: int) -> dict:
        return self._goal_transition(identity, "complete", ("review",), "completed")

    def goal_cancel(self, identity: int, reason: str) -> dict:
        reason = _safe_note(reason, "取消原因")
        with locked(self.paths):
            state = self.state()
            _validate_current(self.paths, state)
            goal = _find(state["target.json"]["targets"], identity, "目标")
            before = goal["status"]
            if before not in ("pending", "active", "blocked", "review"):
                raise GoGoalError(f"目标 G-{identity} 不能从 {before} 取消。")
            timestamp = local_time()
            for entity, key in (("ai", "aiTasks"), ("user", "userTasks")):
                for task in state["task.json"][key]:
                    if task["goalId"] != identity or task["status"] in TERMINAL_STATUSES:
                        continue
                    task_before = task["status"]
                    task["status"] = "cancelled"
                    task["endedAt"] = timestamp
                    if entity == "ai":
                        task["blocker"] = None
                    else:
                        task["result"] = reason
                    note = system_note(state["config.json"]["locale"], "goal_cancel", reason=reason)
                    _append_log(state, entity, task, "cancel", task_before, "cancelled", note)
            goal["status"] = "cancelled"
            goal["endedAt"] = timestamp
            goal["blocker"] = None
            _append_log(state, "goal", goal, "cancel", before, "cancelled", reason)
            _validate_for_write(self.paths, state)
            write_many(self.paths, {
                "target.json": state["target.json"], "task.json": state["task.json"],
                "log.json": state["log.json"],
            })
        return _changed_result(
            f"已取消目标 G-{identity} 及其非终态关联任务。", goal,
            ["target.json", "task.json", "log.json"], _suggested_commit("goal", "cancel", goal),
        )

    def goal_archive(self, identity: int) -> dict:
        with locked(self.paths):
            state = self.state()
            _validate_current(self.paths, state)
            goals = state["target.json"]["targets"]
            goal = _find(goals, identity, "目标")
            if goal["status"] not in TERMINAL_STATUSES:
                raise GoGoalError("只有 completed 或 cancelled 目标可以归档。")
            active_related = [
                (entity, key, item) for entity, key in (("ai", "aiTasks"), ("user", "userTasks"))
                for item in state["task.json"][key] if item["goalId"] == identity
            ]
            if any(item["status"] not in TERMINAL_STATUSES for _, _, item in active_related):
                raise GoGoalError("存在非终态关联任务，不能归档目标。")
            archived_at = local_time()
            for entity, key, task in active_related:
                state["task.json"][key].remove(task)
                task["archivedAt"] = archived_at
                state["task-archive.json"][key].append(task)
                _append_log(state, entity, task, "archive", task["status"], task["status"])
            goals.remove(goal)
            goal["archivedAt"] = archived_at
            state["target-archive.json"]["targets"].append(goal)
            _append_log(state, "goal", goal, "archive", goal["status"], goal["status"])
            _validate_for_write(self.paths, state)
            write_many(self.paths, {
                "target.json": state["target.json"], "target-archive.json": state["target-archive.json"],
                "task.json": state["task.json"], "task-archive.json": state["task-archive.json"],
                "log.json": state["log.json"],
            })
        return _changed_result(
            f"已归档目标 G-{identity} 及仍在活动区的终态关联任务。", goal,
            ["target.json", "target-archive.json", "task.json", "task-archive.json", "log.json"],
            _suggested_commit("goal", "archive", goal),
        )

    def task_create(
        self, entity: str, goal_id: int, title: str, description: str,
        kind: str | None = None,
    ) -> dict:
        if entity not in ("ai", "user"):
            raise GoGoalError("任务类型只允许 ai 或 user。")
        title, description = _safe_title(title), _safe_content(description, "描述")
        if entity == "ai" and kind is not None:
            raise GoGoalError("AI 任务不接受 --kind。")
        if entity == "user" and kind not in USER_KINDS:
            raise GoGoalError("用户任务 kind 只允许 dependency、decision 或 other。")
        with locked(self.paths):
            state = self.state()
            _validate_current(self.paths, state)
            goal = _find(state["target.json"]["targets"], goal_id, "目标")
            if goal["status"] != "active":
                raise GoGoalError("只有 active 目标可以新增任务。")
            key = "aiTasks" if entity == "ai" else "userTasks"
            identity = _next_id(state["task.json"][key], state["task-archive.json"][key])
            record: dict[str, Any] = {
                "id": identity, "title": title, "description": description,
                "status": "pending", "goalId": goal_id,
                "recordedAt": local_time(), "endedAt": None,
            }
            if entity == "ai":
                record.update({"document": f"tasks/{identity}.md", "blocker": None})
            else:
                record.update({"kind": kind, "result": None})
            state["task.json"][key].append(record)
            _append_log(state, entity, record, "create", None, "pending")
            _validate_for_write(self.paths, state)
            write_many(self.paths, {"task.json": state["task.json"], "log.json": state["log.json"]})
        followup = f"；请按写作指南创建 {record['document']}" if entity == "ai" else ""
        prefix = "A" if entity == "ai" else "U"
        label = "AI任务" if entity == "ai" else "用户任务"
        return _changed_result(
            f"已登记{label} {prefix}-{identity}{followup}。", record,
            ["task.json", "log.json"], _suggested_commit(entity, "create", record),
        )

    def task_update(self, identity: int, entity: str, title: str | None, description: str | None) -> dict:
        if title is None and description is None:
            raise GoGoalError("至少提供 --title 或 --description。")
        key = "aiTasks" if entity == "ai" else "userTasks"
        allowed = ("pending", "active", "blocked") if entity == "ai" else ("pending",)
        with locked(self.paths):
            state = self.state()
            _validate_current(self.paths, state)
            record = _find(state["task.json"][key], identity, f"{entity}任务")
            if record["status"] not in allowed:
                raise GoGoalError("当前任务状态不允许更新。")
            changes: list[str] = []
            if title is not None:
                record["title"] = _safe_title(title)
                changes.append("title")
            if description is not None:
                record["description"] = _safe_content(description, "描述")
                changes.append("description")
            note = system_note(state["config.json"]["locale"], "update", fields=changes)
            _append_log(state, entity, record, "update", record["status"], record["status"], note)
            _validate_for_write(self.paths, state)
            write_many(self.paths, {"task.json": state["task.json"], "log.json": state["log.json"]})
        prefix = "A" if entity == "ai" else "U"
        return _changed_result(
            f"已更新任务 {prefix}-{identity}；AI 任务标题变化时请同步 Markdown 一级标题。",
            record, ["task.json", "log.json"], _suggested_commit(entity, "update", record),
        )

    def _capacity_from_state(self, state: dict[str, Any]) -> tuple[int, int]:
        config = state["config.json"]
        git = git_capability(self.paths.root, config["git"]["enabled"])
        parallel_isolation = bool(
            config["git"]["enabled"] and git["available"] and git["repository"] and git["worktree"]
        )
        effective = config["execution"]["maxParallelTasks"] if parallel_isolation else 1
        active = sum(item["status"] == "active" for item in state["task.json"]["aiTasks"])
        return effective, active

    def _ai_transition(
        self, identity: int, action: str, allowed: tuple[str, ...], target: str,
        note: str | None = None, blocker: dict | None = None,
    ) -> dict:
        with locked(self.paths):
            state = self.state()
            _validate_current(self.paths, state)
            record = _find(state["task.json"]["aiTasks"], identity, "AI任务")
            before = record["status"]
            if before not in allowed:
                raise GoGoalError(f"AI 任务 A-{identity} 不能从 {before} 执行 {action}。")
            goal = _find(state["target.json"]["targets"], record["goalId"], "目标")
            if action in ("start", "resume") and goal["status"] != "active":
                raise GoGoalError("关联目标不是 active，不能启动或恢复 AI 任务。")
            if action == "start":
                effective, active = self._capacity_from_state(state)
                if active >= effective:
                    raise GoGoalError(f"已达到有效并行上限 {effective}，任务保持 pending。")
            record["status"] = target
            record["blocker"] = blocker
            record["endedAt"] = local_time() if target in TERMINAL_STATUSES else None
            _append_log(state, "ai", record, action, before, target, note)
            _validate_for_write(self.paths, state)
            write_many(self.paths, {"task.json": state["task.json"], "log.json": state["log.json"]})
        return _changed_result(
            f"AI 任务 A-{identity} 已执行 {action}，当前状态为 {target}。",
            record, ["task.json", "log.json"], _suggested_commit("ai", action, record),
        )

    def task_start(self, identity: int) -> dict:
        return self._ai_transition(identity, "start", ("pending",), "active")

    def task_block(self, identity: int, reason: str, condition: str) -> dict:
        reason, condition = _safe_note(reason, "阻塞原因"), _safe_note(condition, "解除条件")
        note = system_note(self.config_get("locale"), "block", reason=reason, condition=condition)
        return self._ai_transition(
            identity, "block", ("active",), "blocked",
            note, {"reason": reason, "condition": condition},
        )

    def task_resume(self, identity: int) -> dict:
        return self._ai_transition(identity, "resume", ("blocked",), "active", system_note(self.config_get("locale"), "resume"))

    def task_complete_ai(self, identity: int) -> dict:
        return self._ai_transition(identity, "complete", ("active",), "completed")

    def task_cancel_ai(self, identity: int, reason: str) -> dict:
        return self._ai_transition(
            identity, "cancel", ("pending", "active", "blocked"), "cancelled",
            _safe_note(reason, "取消原因"),
        )

    def task_finish_user(self, identity: int, action: str, result: str) -> dict:
        result = _safe_note(result, "用户任务结果")
        if action not in ("complete", "cancel"):
            raise GoGoalError("用户任务只允许 complete 或 cancel。")
        target = "completed" if action == "complete" else "cancelled"
        with locked(self.paths):
            state = self.state()
            _validate_current(self.paths, state)
            record = _find(state["task.json"]["userTasks"], identity, "用户任务")
            if record["status"] != "pending":
                raise GoGoalError("只有 pending 用户任务可以完成或取消。")
            record["status"] = target
            record["result"] = result
            record["endedAt"] = local_time()
            _append_log(state, "user", record, action, "pending", target, result)
            _validate_for_write(self.paths, state)
            write_many(self.paths, {"task.json": state["task.json"], "log.json": state["log.json"]})
        return _changed_result(
            f"用户任务 U-{identity} 已{action}。", record,
            ["task.json", "log.json"], _suggested_commit("user", action, record),
        )

    def task_archive(self, identity: int, entity: str) -> dict:
        key = "aiTasks" if entity == "ai" else "userTasks"
        with locked(self.paths):
            state = self.state()
            _validate_current(self.paths, state)
            active = state["task.json"][key]
            record = _find(active, identity, f"{entity}任务")
            if record["status"] not in TERMINAL_STATUSES:
                raise GoGoalError("只有 completed 或 cancelled 任务可以归档。")
            active.remove(record)
            record["archivedAt"] = local_time()
            state["task-archive.json"][key].append(record)
            _append_log(state, entity, record, "archive", record["status"], record["status"])
            _validate_for_write(self.paths, state)
            write_many(self.paths, {
                "task.json": state["task.json"], "task-archive.json": state["task-archive.json"],
                "log.json": state["log.json"],
            })
        prefix = "A" if entity == "ai" else "U"
        return _changed_result(
            f"已归档任务 {prefix}-{identity}。", record,
            ["task.json", "task-archive.json", "log.json"],
            _suggested_commit(entity, "archive", record),
        )
