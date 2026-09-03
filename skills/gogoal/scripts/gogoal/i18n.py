"""CLI 与本地服务的轻量双语资源。"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

SUPPORTED_LOCALES = ("zh-CN", "en-US")

UI = {
    "zh-CN": {
        "cli_description": "目标与任务管理 Skill CLI",
        "json": "输出稳定 JSON",
        "positive_integer": "必须是正整数",
        "task_type": "任务类型",
        "project_root": "显式指定项目根目录",
        "init": "初始化项目数据目录",
        "project": "看板项目名称",
        "config": "查询或修改配置",
        "config_list": "列出配置",
        "config_get": "读取配置项",
        "config_set": "修改配置项",
        "summary": "显示目标任务摘要",
        "archive": "包含归档",
        "validate": "校验全部管理数据",
        "strict": "警告也视为失败",
        "goal": "管理目标",
        "goal_list": "列出目标",
        "task": "管理任务",
        "log": "查询管理日志",
        "dashboard": "启动只读看板",
        "changed_files": "修改文件：",
        "suggested_commit": "建议提交：",
        "error": "错误：",
        "stopped": "已停止。",
        "dashboard_url": "GoGoal 只读看板：{url}",
        "dashboard_stop": "按 Ctrl+C 停止服务。",
    },
    "en-US": {
        "cli_description": "Goal and task management Skill CLI",
        "json": "Output stable JSON",
        "positive_integer": "must be a positive integer",
        "task_type": "Task type",
        "project_root": "Explicit project root",
        "init": "Initialize project data",
        "project": "Dashboard project name",
        "config": "Read or update configuration",
        "config_list": "List configuration",
        "config_get": "Read a configuration value",
        "config_set": "Update a configuration value",
        "summary": "Show goal and task summary",
        "archive": "Include archived records",
        "validate": "Validate all management data",
        "strict": "Treat warnings as errors",
        "goal": "Manage goals",
        "goal_list": "List goals",
        "task": "Manage tasks",
        "log": "Query management log",
        "dashboard": "Start the read-only dashboard",
        "changed_files": "Changed files: ",
        "suggested_commit": "Suggested commit: ",
        "error": "Error: ",
        "stopped": "Stopped.",
        "dashboard_url": "GoGoal read-only dashboard: {url}",
        "dashboard_stop": "Press Ctrl+C to stop the server.",
    },
}

STATUS = {
    "zh-CN": {
        "pending": "待处理", "active": "进行中", "blocked": "已阻塞",
        "review": "待验收", "completed": "已完成", "cancelled": "已取消",
    },
    "en-US": {
        "pending": "Pending", "active": "Active", "blocked": "Blocked",
        "review": "Review", "completed": "Completed", "cancelled": "Cancelled",
    },
}

ACTION = {
    "zh-CN": {
        "create": "登记", "update": "更新", "start": "启动", "block": "阻塞",
        "resume": "恢复", "submit": "提交验收", "revise": "验收修改",
        "complete": "完成", "cancel": "取消", "archive": "归档",
    },
    "en-US": {
        "create": "Created", "update": "Updated", "start": "Started", "block": "Blocked",
        "resume": "Resumed", "submit": "Submitted", "revise": "Revised",
        "complete": "Completed", "cancel": "Cancelled", "archive": "Archived",
    },
}

EXACT_EN = {
    "校验通过。": "Validation passed.",
    "用户任务没有 start 命令。": "User tasks do not support the start command.",
    "用户任务不能进入 blocked。": "User tasks cannot enter blocked status.",
    "用户任务没有 resume 命令。": "User tasks do not support the resume command.",
    "AI 任务 complete 不接受 --result。": "AI task complete does not accept --result.",
    "AI 任务 cancel 使用 --reason，不接受 --result。": "AI task cancel uses --reason and does not accept --result.",
    "用户任务 cancel 使用 --result，不接受 --reason。": "User task cancel uses --result and does not accept --reason.",
    "使用 --id 时必须同时指定 --entity。": "--id requires --entity.",
    "--limit 必须大于等于 1。": "--limit must be at least 1.",
    "无法识别命令。": "Unknown command.",
    "GoGoal 项目已初始化。": "GoGoal project initialized.",
    "项目已经初始化；重复初始化不会覆盖现有数据或写作指南。": "The project is already initialized; repeated initialization will not overwrite data or writing guides.",
    "初始化期间检测到已存在管理文件，已停止以避免覆盖。": "Management files appeared during initialization; initialization stopped to avoid overwriting them.",
    "Skill 缺少默认写作指南，无法初始化。": "The Skill is missing default writing guides and cannot initialize the project.",
    "format 不能通过 config set 修改。": "format cannot be changed with config set.",
    "至少提供 --title 或 --description。": "Provide at least --title or --description.",
    "终态或归档目标不能更新。": "Terminal or archived goals cannot be updated.",
    "目标阻塞前必须先完成或阻塞全部 active AI 任务。": "Complete or block every active AI task before blocking the goal.",
    "仍有关联任务不是终态，不能提交目标验收。": "All related tasks must be terminal before submitting the goal for review.",
    "只有 completed 或 cancelled 目标可以归档。": "Only completed or cancelled goals can be archived.",
    "存在非终态关联任务，不能归档目标。": "The goal cannot be archived while a related task is non-terminal.",
    "任务类型只允许 ai 或 user。": "Task type must be ai or user.",
    "AI 任务不接受 --kind。": "AI tasks do not accept --kind.",
    "用户任务 kind 只允许 dependency、decision 或 other。": "User task kind must be dependency, decision, or other.",
    "只有 active 目标可以新增任务。": "Tasks can only be created for an active goal.",
    "当前任务状态不允许更新。": "The current task status does not allow updates.",
    "关联目标不是 active，不能启动或恢复 AI 任务。": "The related goal is not active, so the AI task cannot start or resume.",
    "用户任务只允许 complete 或 cancel。": "User tasks only support complete or cancel.",
    "只有 pending 用户任务可以完成或取消。": "Only pending user tasks can be completed or cancelled.",
    "只有 completed 或 cancelled 任务可以归档。": "Only completed or cancelled tasks can be archived.",
    "未找到 gogoal/config.json；请在项目目录运行 gogoal init。": "gogoal/config.json was not found; run gogoal init in the project directory.",
    "写入管理数据失败，已尝试恢复动作前状态。": "Writing management data failed; GoGoal attempted to restore the previous state.",
    "对象文档路径超出 gogoal/ 目录。": "The object document path escapes the gogoal/ directory.",
    "无法获取 GoGoal 管理文件锁。": "Unable to acquire the GoGoal management lock.",
    "看板端口必须是 1 到 65535 的整数。": "Dashboard port must be an integer from 1 to 65535.",
    "Skill 缺少看板前端资源。": "The Skill is missing dashboard assets.",
    "标题必须是单行文本。": "The title must be a single line.",
    "locale 只允许 zh-CN 或 en-US。": "locale must be zh-CN or en-US.",
    "不兼容的数据格式：仅支持 format=1，拒绝修改。": "Incompatible data format: only format=1 is supported; refusing to modify data.",
}

ERROR_LABELS_EN = {
    "项目名称": "Project name",
    "标题": "Title",
    "描述": "Description",
    "阻塞原因": "Blocker reason",
    "解除条件": "Recovery condition",
    "验收修改摘要": "Review revision note",
    "取消原因": "Cancellation reason",
    "用户任务结果": "User task result",
}

PATTERNS_EN: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"^已更新配置 (.+)。$"), r"Updated configuration \1."),
    (re.compile(r"^检测到未完成初始化留下的管理文件；为避免覆盖，请先人工检查：(.+)$"), r"Management files from an incomplete initialization were found; inspect them before retrying to avoid overwriting: \1"),
    (re.compile(r"^已登记目标 G-(\d+)；请按写作指南创建 (.+)。$"), r"Created goal G-\1; create \2 using the writing guide."),
    (re.compile(r"^已更新目标 G-(\d+)；标题变化时请同步 Markdown 一级标题。$"), r"Updated goal G-\1; synchronize the Markdown H1 when the title changes."),
    (re.compile(r"^目标 G-(\d+) 已执行 (\w+)，当前状态为 (\w+)。$"), r"Goal G-\1 executed \2; current status: \3."),
    (re.compile(r"^已取消目标 G-(\d+) 及其非终态关联任务。$"), r"Cancelled goal G-\1 and its non-terminal related tasks."),
    (re.compile(r"^已归档目标 G-(\d+) 及仍在活动区的终态关联任务。$"), r"Archived goal G-\1 and its terminal related tasks still in active storage."),
    (re.compile(r"^已登记AI任务 A-(\d+)；请按写作指南创建 (.+)。$"), r"Created AI task A-\1; create \2 using the writing guide."),
    (re.compile(r"^已登记用户任务 U-(\d+)。$"), r"Created user task U-\1."),
    (re.compile(r"^已更新任务 ([AU])-([0-9]+)；AI 任务标题变化时请同步 Markdown 一级标题。$"), r"Updated task \1-\2; synchronize the Markdown H1 when an AI task title changes."),
    (re.compile(r"^AI 任务 A-(\d+) 已执行 (\w+)，当前状态为 (\w+)。$"), r"AI task A-\1 executed \2; current status: \3."),
    (re.compile(r"^用户任务 U-(\d+) 已(complete|cancel)。$"), r"User task U-\1 executed \2."),
    (re.compile(r"^已归档任务 ([AU])-(\d+)。$"), r"Archived task \1-\2."),
    (re.compile(r"^不存在配置项：(.+)$"), r"Unknown configuration path: \1"),
    (re.compile(r"^未找到目标 (\d+)。$"), r"Goal \1 was not found."),
    (re.compile(r"^未找到(ai|user)任务 (\d+)。$"), r"\1 task \2 was not found."),
    (re.compile(r"^未找到(.+) (\d+)。$"), r"\1 \2 was not found."),
    (re.compile(r"^目标 G-(\d+) 不能从 (\w+) 执行 (\w+)。$"), r"Goal G-\1 cannot execute \3 from \2."),
    (re.compile(r"^目标 G-(\d+) 不能从 (\w+) 取消。$"), r"Goal G-\1 cannot be cancelled from \2."),
    (re.compile(r"^AI 任务 A-(\d+) 不能从 (\w+) 执行 (\w+)。$"), r"AI task A-\1 cannot execute \3 from \2."),
    (re.compile(r"^已达到有效并行上限 (\d+)，任务保持 pending。$"), r"The effective parallel limit \1 has been reached; the task remains pending."),
    (re.compile(r"^缺少必需文件：(.+)$"), r"Missing required file: \1"),
    (re.compile(r"^无法读取有效 JSON：(.+)$"), r"Unable to read valid JSON: \1"),
    (re.compile(r"^无法监听 (.+)，请检查端口或配置。$"), r"Unable to listen on \1; check the port and configuration."),
    (re.compile(r"^(.+)必须是单行文本且不能包含控制字符。$"), r"\1 must be a single line without control characters."),
    (re.compile(r"^(.+)不能包含控制字符。$"), r"\1 must not contain control characters."),
)

# 校验器会组合文件路径和字段名；以下长短语替换让诊断保持可读，
# 同时保留稳定的路径、字段名、状态值和编号。
VALIDATION_PHRASES_EN = (
    ("严格模式警告：", "Strict-mode warning: "),
    ("配置值非法：", "Invalid configuration value: "),
    ("初始化配置非法：", "Invalid initialization configuration: "),
    ("管理数据不一致：", "Management data is inconsistent: "),
    ("现有管理数据或文档不一致，请先修复并运行 validate：", "Existing management data or documents are inconsistent; repair them and run validate first: "),
    ("校验失败：", "Validation failed:"),
    ("blocked 状态必须包含非空 blocker.reason 和 blocker.condition", "in blocked status must contain non-empty blocker.reason and blocker.condition"),
    ("非 blocked 状态的 blocker 必须为 null", "blocker must be null outside blocked status"),
    ("endedAt 必须且仅能在终态为有效本地时间", "endedAt must be a valid local time if and only if the record is terminal"),
    ("归档记录必须是终态且包含 archivedAt", "archived record must be terminal and contain archivedAt"),
    ("活动记录不得包含 archivedAt", "active record must not contain archivedAt"),
    ("必须是递增且不重复的正整数", "must be an increasing, unique positive integer"),
    ("必须是大于等于 1 的整数", "must be an integer greater than or equal to 1"),
    ("必须是 1 到 65535 的整数", "must be an integer from 1 to 65535"),
    ("必须是安全的相对前缀并以 / 结尾", "must be a safe relative prefix ending in /"),
    ("必须位于项目仓库之外", "must be outside the project repository"),
    ("必须关联存在的目标", "must reference an existing goal"),
    ("终态用户任务必须包含非空 result", "terminal user task must contain a non-empty result"),
    ("pending 用户任务 result 必须为 null", "pending user task result must be null"),
    ("一级标题必须为：", "H1 must be: "),
    ("文档路径越界", "document path escapes its boundary"),
    ("缺少对象文档：", "Missing object document: "),
    ("无法读取对象文档一级标题：", "Unable to read object document H1: "),
    ("在活动或归档数据中重复", "is duplicated across active or archived data"),
    ("根值必须是对象", "root value must be an object"),
    ("必须是非空字符串", "must be a non-empty string"),
    ("必须是无控制字符的单行文本", "must be a single line without control characters"),
    ("不能包含控制字符", "must not contain control characters"),
    ("必须是非空路径", "must be a non-empty path"),
    ("必须是布尔值", "must be a Boolean"),
    ("必须是正整数", "must be a positive integer"),
    ("必须是数组", "must be an array"),
    ("必须是对象", "must be an object"),
    ("只允许 zh-CN 或 en-US", "must be zh-CN or en-US"),
    ("疑似包含敏感凭据", "may contain sensitive credentials"),
    ("时间或标题非法", "has an invalid time or title"),
    ("引用了不存在或关联错误的对象", "references a missing or incorrectly related object"),
    ("状态链与上一条日志不连续", "status chain is not continuous with the previous log"),
    ("是对象首条日志但动作不是 create", "is the object's first log but its action is not create"),
    ("对同一对象重复记录 create", "repeats create for the same object"),
    ("create 的 statusFrom 必须为 null", "statusFrom must be null for create"),
    ("必须为 null 或非空字符串", "must be null or a non-empty string"),
    ("缺少管理日志", "is missing a management log"),
    ("当前状态与日志末状态不一致", "current status differs from the final log status"),
    ("不属于", "does not belong to"),
    ("动作枚举", "action enumeration"),
    ("非法", "is invalid"),
    ("缺少项目写作指南：", "Missing project writing guide: "),
    ("无法读取项目写作指南：", "Unable to read project writing guide: "),
    ("项目写作指南不能为空：", "Project writing guide must not be empty: "),
    ("项目写作指南疑似包含敏感凭据：", "Project writing guide may contain sensitive credentials: "),
    ("包含未知字段：", "contains unknown fields: "),
    ("缺少字段：", "is missing fields: "),
    ("动作与状态迁移不匹配", "action does not match the status transition"),
    ("当前标题与日志末标题快照不一致", "current title differs from the final log title snapshot"),
)


def ui(locale: str, key: str, **values: object) -> str:
    language = locale if locale in SUPPORTED_LOCALES else "zh-CN"
    return UI[language].get(key, UI["zh-CN"].get(key, key)).format(**values)


def status(locale: str, value: object) -> str:
    return STATUS.get(locale, STATUS["zh-CN"]).get(str(value), str(value))


def action(locale: str, value: object) -> str:
    return ACTION.get(locale, ACTION["zh-CN"]).get(str(value), str(value))


def system_note(locale: str, key: str, **values: object) -> str:
    fields = values.get("fields", [])
    if key == "update":
        labels = {
            "zh-CN": {"title": "标题", "description": "描述"},
            "en-US": {"title": "title", "description": "description"},
        }[locale if locale in SUPPORTED_LOCALES else "zh-CN"]
        names = [labels.get(str(field), str(field)) for field in fields if str(field) in labels]
        return ("更新" + "和".join(names)) if locale != "en-US" else ("Updated " + " and ".join(names))
    if key == "block":
        if locale == "en-US":
            return f"{values['reason']}; recovery condition: {values['condition']}"
        return f"{values['reason']}；解除条件：{values['condition']}"
    if key == "resume":
        return "Blocker resolved" if locale == "en-US" else "阻塞解除"
    if key == "goal_cancel":
        return f"Goal cancelled: {values['reason']}" if locale == "en-US" else f"目标取消：{values['reason']}"
    return str(values.get("value", ""))


def translate(text: str, locale: str) -> str:
    if locale != "en-US":
        return text
    if text in EXACT_EN:
        return EXACT_EN[text]
    for label, translated in ERROR_LABELS_EN.items():
        dynamic_errors = {
            f"{label}不能为空。": f"{translated} must not be empty.",
            f"{label}必须是单行文本且不能包含控制字符。": f"{translated} must be a single line without control characters.",
            f"{label}不能包含控制字符。": f"{translated} must not contain control characters.",
            f"{label}疑似包含敏感凭据，拒绝写入管理数据。": f"{translated} may contain sensitive credentials; refusing to write management data.",
        }
        if text in dynamic_errors:
            return dynamic_errors[text]
    for pattern, replacement in PATTERNS_EN:
        if pattern.fullmatch(text):
            return pattern.sub(replacement, text)
    result = text
    for source, target in VALIDATION_PHRASES_EN:
        result = result.replace(source, target)
    return result


def detect_locale(argv: Iterable[str], cwd: Path) -> str:
    """在完整参数解析前只读探测界面语言；损坏配置安全回退中文。"""
    arguments = list(argv)
    if "init" in arguments and "--locale" in arguments:
        try:
            locale = arguments[arguments.index("--locale") + 1]
            return locale if locale in SUPPORTED_LOCALES else "zh-CN"
        except IndexError:
            return "zh-CN"
    root = cwd
    for index, value in enumerate(arguments):
        if value == "--project-root" and index + 1 < len(arguments):
            root = Path(arguments[index + 1]).expanduser()
        elif value.startswith("--project-root="):
            root = Path(value.split("=", 1)[1]).expanduser()
    try:
        import json

        current = root.resolve()
        for candidate in (current, *current.parents):
            path = candidate / "gogoal" / "config.json"
            if path.is_file():
                value = json.loads(path.read_text(encoding="utf-8")).get("locale")
                return value if value in SUPPORTED_LOCALES else "zh-CN"
    except (OSError, UnicodeError, ValueError, TypeError):
        pass
    return "zh-CN"
