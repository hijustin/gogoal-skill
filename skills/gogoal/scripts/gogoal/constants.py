"""GoGoal 数据常量与默认配置。"""

from __future__ import annotations

import re
from copy import deepcopy

FORMAT_VERSION = 1
GOAL_STATUSES = ("pending", "active", "blocked", "review", "completed", "cancelled")
AI_STATUSES = ("pending", "active", "blocked", "completed", "cancelled")
USER_STATUSES = ("pending", "completed", "cancelled")
TERMINAL_STATUSES = ("completed", "cancelled")
USER_KINDS = ("dependency", "decision", "other")
ENTITIES = ("goal", "ai", "user")
LOCALES = ("zh-CN", "en-US")

SENSITIVE_RE = re.compile(
    r"(?ix)("
    r"(?:password|passwd|secret|token|api[_-]?key|private[_-]?key)\s*[:=]\s*\S+"
    r"|authorization\s*:\s*(?:bearer|basic)\s+\S+"
    r"|-----BEGIN\s+[A-Z ]*PRIVATE\s+KEY-----"
    r"|\bAKIA[A-Z0-9]{16}\b"
    r"|\bgh[opusr]_[A-Za-z0-9]{20,}\b"
    r"|\bsk-[A-Za-z0-9_-]{20,}\b"
    r"|https?://[^/\s:@]+:[^@\s/]+@"
    r")"
)
ILLEGAL_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

GOAL_ACTIONS = ("create", "update", "start", "block", "resume", "submit", "revise", "complete", "cancel", "archive")
AI_ACTIONS = ("create", "update", "start", "block", "resume", "complete", "cancel", "archive")
USER_ACTIONS = ("create", "update", "complete", "cancel", "archive")

DEFAULT_CONFIG = {
    "format": FORMAT_VERSION,
    "project": "",
    "locale": "zh-CN",
    "execution": {"maxParallelTasks": 2},
    "git": {
        "enabled": True,
        "autoCommit": True,
        "branchPrefix": "gogoal/",
        "worktreeRoot": "../.gogoal-worktrees",
    },
    "dashboard": {
        "host": "127.0.0.1",
        "port": 4173,
        "refreshSeconds": 180,
        "autoOpen": False,
        "gitActivity": True,
    },
}

EMPTY_FILES = {
    "target.json": {"targets": []},
    "target-archive.json": {"targets": []},
    "task.json": {"aiTasks": [], "userTasks": []},
    "task-archive.json": {"aiTasks": [], "userTasks": []},
    "log.json": {"logs": []},
}


def new_config() -> dict:
    return deepcopy(DEFAULT_CONFIG)
