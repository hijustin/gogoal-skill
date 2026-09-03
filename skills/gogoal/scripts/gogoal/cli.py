"""GoGoal 命令行解析与输出。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from . import __version__
from .constants import AI_ACTIONS, AI_STATUSES, GOAL_ACTIONS, GOAL_STATUSES, USER_ACTIONS, USER_KINDS, USER_STATUSES
from .errors import GoGoalError
from .i18n import action as action_label
from .i18n import detect_locale, status as status_label, translate, ui
from .service import GoGoalService


def _json_flag(parser: argparse.ArgumentParser, locale: str) -> None:
    parser.add_argument("--json", action="store_true", help=ui(locale, "json"))


def _positive_int(locale: str):
    def parse(raw: str) -> int:
        try:
            value = int(raw)
        except ValueError as exc:
            raise argparse.ArgumentTypeError(ui(locale, "positive_integer")) from exc
        if value < 1:
            raise argparse.ArgumentTypeError(ui(locale, "positive_integer"))
        return value

    return parse


def _task_type(parser: argparse.ArgumentParser, locale: str) -> None:
    parser.add_argument("--type", choices=("ai", "user"), required=True, help=ui(locale, "task_type"))


def build_parser(locale: str = "zh-CN") -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="gogoal", description=ui(locale, "cli_description"))
    parser.add_argument("--version", action="version", version=f"gogoal {__version__}")
    parser.add_argument("--project-root", type=Path, help=ui(locale, "project_root"))
    commands = parser.add_subparsers(dest="command", required=True)

    init = commands.add_parser("init", help=ui(locale, "init"))
    init.add_argument("--project", help=ui(locale, "project"))
    init.add_argument("--locale", choices=("zh-CN", "en-US"), default="zh-CN")
    _json_flag(init, locale)

    config = commands.add_parser("config", help=ui(locale, "config")).add_subparsers(dest="config_command", required=True)
    config_list = config.add_parser("list", help=ui(locale, "config_list"))
    _json_flag(config_list, locale)
    config_get = config.add_parser("get", help=ui(locale, "config_get"))
    config_get.add_argument("path")
    _json_flag(config_get, locale)
    config_set = config.add_parser("set", help=ui(locale, "config_set"))
    config_set.add_argument("path")
    config_set.add_argument("value")
    _json_flag(config_set, locale)

    summary = commands.add_parser("summary", help=ui(locale, "summary"))
    summary.add_argument("--archive", action="store_true", help=ui(locale, "archive"))
    _json_flag(summary, locale)
    validate = commands.add_parser("validate", help=ui(locale, "validate"))
    validate.add_argument("--strict", action="store_true", help=ui(locale, "strict"))
    _json_flag(validate, locale)

    goal_parser = commands.add_parser("goal", help=ui(locale, "goal"))
    goal = goal_parser.add_subparsers(dest="goal_command", required=True)
    goal_list = goal.add_parser("list", help=ui(locale, "goal_list"))
    goal_list.add_argument("--status", choices=GOAL_STATUSES)
    group = goal_list.add_mutually_exclusive_group()
    group.add_argument("--archive", action="store_true")
    group.add_argument("--all", action="store_true")
    _json_flag(goal_list, locale)
    for name in ("show", "context", "start", "resume", "submit", "complete", "archive"):
        item = goal.add_parser(name)
        item.add_argument("id", type=_positive_int(locale))
        _json_flag(item, locale)
    goal_create = goal.add_parser("create")
    goal_create.add_argument("--title", required=True)
    goal_create.add_argument("--description", required=True)
    _json_flag(goal_create, locale)
    goal_update = goal.add_parser("update")
    goal_update.add_argument("id", type=_positive_int(locale))
    goal_update.add_argument("--title")
    goal_update.add_argument("--description")
    _json_flag(goal_update, locale)
    goal_block = goal.add_parser("block")
    goal_block.add_argument("id", type=_positive_int(locale))
    goal_block.add_argument("--reason", required=True)
    goal_block.add_argument("--condition", required=True)
    _json_flag(goal_block, locale)
    goal_revise = goal.add_parser("revise")
    goal_revise.add_argument("id", type=_positive_int(locale))
    goal_revise.add_argument("--note", required=True)
    _json_flag(goal_revise, locale)
    goal_cancel = goal.add_parser("cancel")
    goal_cancel.add_argument("id", type=_positive_int(locale))
    goal_cancel.add_argument("--reason", required=True)
    _json_flag(goal_cancel, locale)

    task_parser = commands.add_parser("task", help=ui(locale, "task"))
    task = task_parser.add_subparsers(dest="task_command", required=True)
    task_list = task.add_parser("list")
    task_list.add_argument("--goal", type=_positive_int(locale))
    task_list.add_argument("--type", choices=("ai", "user"))
    task_list.add_argument("--status", choices=tuple(sorted(set((*AI_STATUSES, *USER_STATUSES)))))
    group = task_list.add_mutually_exclusive_group()
    group.add_argument("--archive", action="store_true")
    group.add_argument("--all", action="store_true")
    _json_flag(task_list, locale)
    task_capacity = task.add_parser("capacity")
    _json_flag(task_capacity, locale)
    task_show = task.add_parser("show")
    task_show.add_argument("id", type=_positive_int(locale))
    _task_type(task_show, locale)
    _json_flag(task_show, locale)
    task_create = task.add_parser("create")
    _task_type(task_create, locale)
    task_create.add_argument("--goal", type=_positive_int(locale), required=True)
    task_create.add_argument("--kind", choices=USER_KINDS)
    task_create.add_argument("--title", required=True)
    task_create.add_argument("--description", required=True)
    _json_flag(task_create, locale)
    task_update = task.add_parser("update")
    task_update.add_argument("id", type=_positive_int(locale))
    _task_type(task_update, locale)
    task_update.add_argument("--title")
    task_update.add_argument("--description")
    _json_flag(task_update, locale)
    for name in ("start", "resume"):
        item = task.add_parser(name)
        item.add_argument("id", type=_positive_int(locale))
        _task_type(item, locale)
        _json_flag(item, locale)
    task_block = task.add_parser("block")
    task_block.add_argument("id", type=_positive_int(locale))
    _task_type(task_block, locale)
    task_block.add_argument("--reason", required=True)
    task_block.add_argument("--condition", required=True)
    _json_flag(task_block, locale)
    task_complete = task.add_parser("complete")
    task_complete.add_argument("id", type=_positive_int(locale))
    _task_type(task_complete, locale)
    task_complete.add_argument("--result")
    _json_flag(task_complete, locale)
    task_cancel = task.add_parser("cancel")
    task_cancel.add_argument("id", type=_positive_int(locale))
    _task_type(task_cancel, locale)
    task_cancel.add_argument("--reason")
    task_cancel.add_argument("--result")
    _json_flag(task_cancel, locale)
    task_archive = task.add_parser("archive")
    task_archive.add_argument("id", type=_positive_int(locale))
    _task_type(task_archive, locale)
    _json_flag(task_archive, locale)

    log_parser = commands.add_parser("log", help=ui(locale, "log"))
    log = log_parser.add_subparsers(dest="log_command", required=True)
    log_list = log.add_parser("list")
    log_list.add_argument("--limit", type=_positive_int(locale), default=20)
    log_list.add_argument("--goal", type=_positive_int(locale))
    log_list.add_argument("--entity", choices=("goal", "ai", "user"))
    log_list.add_argument("--id", type=_positive_int(locale))
    log_list.add_argument("--action", choices=tuple(sorted(set((*GOAL_ACTIONS, *AI_ACTIONS, *USER_ACTIONS)))))
    _json_flag(log_list, locale)
    log_show = log.add_parser("show")
    log_show.add_argument("id", type=_positive_int(locale))
    _json_flag(log_show, locale)

    dashboard_parser = commands.add_parser("dashboard", help=ui(locale, "dashboard"))
    dashboard = dashboard_parser.add_subparsers(dest="dashboard_command", required=True)
    serve = dashboard.add_parser("serve")
    serve.add_argument("--host")
    serve.add_argument("--port", type=int)
    serve.add_argument("--open", action="store_true", dest="open_browser")
    return parser


def _parse_value(raw: str) -> Any:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def _localized_payload(value: Any, locale: str) -> Any:
    if isinstance(value, list):
        return [_localized_payload(item, locale) for item in value]
    if not isinstance(value, dict):
        return value
    result = dict(value)
    if isinstance(result.get("message"), str):
        result["message"] = translate(result["message"], locale)
    for key in ("errors", "warnings"):
        if isinstance(result.get(key), list):
            result[key] = [translate(item, locale) if isinstance(item, str) else item for item in result[key]]
    return result


def _emit(value: Any, as_json: bool, locale: str) -> None:
    value = _localized_payload(value, locale)
    if as_json:
        print(json.dumps(value, ensure_ascii=False, indent=2))
        return
    if isinstance(value, dict) and "message" in value:
        print(value["message"])
        if value.get("record"):
            record = value["record"]
            print(f"{record.get('id')}\t{status_label(locale, record.get('status'))}\t{record.get('title')}")
        if value.get("changedFiles"):
            print(ui(locale, "changed_files") + ", ".join(value["changedFiles"]))
        if value.get("suggestedCommit"):
            print(ui(locale, "suggested_commit") + value["suggestedCommit"])
        return
    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                prefix = {"goal": "G", "ai": "A", "user": "U"}.get(item.get("entity"), "")
                identity = item.get("entityId", item.get("id", ""))
                if "time" in item:
                    print(f"{item.get('id')}\t{item.get('time')}\t{prefix}-{identity}\t{action_label(locale, item.get('action'))}\t{item.get('title')}")
                else:
                    print(f"{identity}\t{status_label(locale, item.get('status'))}\t{item.get('title')}")
            else:
                print(item)
        return
    if isinstance(value, (dict, list)):
        print(json.dumps(value, ensure_ascii=False, separators=(",", ":")))
    else:
        print(value)


def dispatch(args: argparse.Namespace, skill_root: Path) -> Any:
    root = (args.project_root or Path.cwd()).resolve()
    if args.command == "init":
        return GoGoalService.initialize(skill_root, root, args.project, args.locale)
    service = GoGoalService.locate(skill_root, root)
    if args.command == "config":
        if args.config_command == "list":
            return service.config_list()
        if args.config_command == "get":
            return service.config_get(args.path)
        return service.config_set(args.path, _parse_value(args.value))
    if args.command == "summary":
        return service.summary(args.archive)
    if args.command == "validate":
        result = service.validate(args.strict)
        if not result["valid"]:
            raise GoGoalError("校验失败：\n- " + "\n- ".join(result["errors"]))
        return {"message": "校验通过。", **result}
    if args.command == "goal":
        action = args.goal_command
        if action == "list":
            mode = "all" if args.all else "archive" if args.archive else "active"
            records = service.goal_records(mode)
            return [item for item in records if not args.status or item["status"] == args.status]
        if action == "show": return service.goal_show(args.id)
        if action == "context": return service.goal_context(args.id)
        if action == "create": return service.goal_create(args.title, args.description)
        if action == "update": return service.goal_update(args.id, args.title, args.description)
        if action == "start": return service.goal_start(args.id)
        if action == "block": return service.goal_block(args.id, args.reason, args.condition)
        if action == "resume": return service.goal_resume(args.id)
        if action == "submit": return service.goal_submit(args.id)
        if action == "revise": return service.goal_revise(args.id, args.note)
        if action == "complete": return service.goal_complete(args.id)
        if action == "cancel": return service.goal_cancel(args.id, args.reason)
        if action == "archive": return service.goal_archive(args.id)
    if args.command == "task":
        action = args.task_command
        if action == "list":
            mode = "all" if args.all else "archive" if args.archive else "active"
            records = service.task_records(mode)
            entities = (args.type,) if args.type else ("ai", "user")
            result = []
            for entity in entities:
                for item in records["aiTasks" if entity == "ai" else "userTasks"]:
                    if args.goal and item["goalId"] != args.goal: continue
                    if args.status and item["status"] != args.status: continue
                    result.append({"entity": entity, **item})
            return result
        if action == "capacity": return service.capacity()
        if action == "show": return service.task_show(args.id, args.type)
        if action == "create": return service.task_create(args.type, args.goal, args.title, args.description, args.kind)
        if action == "update": return service.task_update(args.id, args.type, args.title, args.description)
        if action == "start":
            if args.type != "ai": raise GoGoalError("用户任务没有 start 命令。")
            return service.task_start(args.id)
        if action == "block":
            if args.type != "ai": raise GoGoalError("用户任务不能进入 blocked。")
            return service.task_block(args.id, args.reason, args.condition)
        if action == "resume":
            if args.type != "ai": raise GoGoalError("用户任务没有 resume 命令。")
            return service.task_resume(args.id)
        if action == "complete":
            if args.type == "ai":
                if args.result is not None: raise GoGoalError("AI 任务 complete 不接受 --result。")
                return service.task_complete_ai(args.id)
            return service.task_finish_user(args.id, "complete", args.result)
        if action == "cancel":
            if args.type == "ai":
                if args.result is not None: raise GoGoalError("AI 任务 cancel 使用 --reason，不接受 --result。")
                return service.task_cancel_ai(args.id, args.reason)
            if args.reason is not None: raise GoGoalError("用户任务 cancel 使用 --result，不接受 --reason。")
            return service.task_finish_user(args.id, "cancel", args.result)
        if action == "archive": return service.task_archive(args.id, args.type)
    if args.command == "log":
        if args.log_command == "show": return service.log_show(args.id)
        records = service.log_list()
        if args.id and not args.entity: raise GoGoalError("使用 --id 时必须同时指定 --entity。")
        if args.goal: records = [item for item in records if item["goalId"] == args.goal]
        if args.entity: records = [item for item in records if item["entity"] == args.entity]
        if args.id: records = [item for item in records if item["entityId"] == args.id]
        if args.action: records = [item for item in records if item["action"] == args.action]
        if args.limit < 1: raise GoGoalError("--limit 必须大于等于 1。")
        return list(reversed(records[-args.limit:]))
    if args.command == "dashboard":
        from .dashboard import serve

        return serve(service, args.host, args.port, args.open_browser)
    raise GoGoalError("无法识别命令。")


def run(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    locale = detect_locale(arguments, Path.cwd())
    parser = build_parser(locale)
    args = parser.parse_args(arguments)
    skill_root = Path(__file__).resolve().parents[2]
    try:
        result = dispatch(args, skill_root)
        if args.command != "dashboard":
            if args.command == "init":
                locale = args.locale
            elif args.command == "config" and args.config_command == "set" and args.path == "locale" and args.value in ("zh-CN", "en-US"):
                locale = args.value
            _emit(result, bool(getattr(args, "json", False)), locale)
        return 0
    except GoGoalError as exc:
        print(ui(locale, "error") + translate(str(exc), locale), file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print(ui(locale, "stopped"), file=sys.stderr)
        return 130
