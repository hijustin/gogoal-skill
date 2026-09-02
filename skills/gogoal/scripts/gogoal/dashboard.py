"""GoGoal 本地只读看板 HTTP 服务。"""

from __future__ import annotations

import json
import mimetypes
import re
import socket
import subprocess
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from .errors import GoGoalError
from .i18n import ui
from .platform import git_capability, local_time
from .service import GoGoalService
from .storage import locked, safe_document_path
from .validation import validate_state

DOCUMENT_RE = re.compile(r"^(targets|tasks)/[1-9]\d*\.md$")
COMMIT_RE = re.compile(
    r"^(目标|AI任务|用户任务)-(登记|更新|启动|实现|阻塞|恢复|待验收|验收修改|完成|取消|归档)-([GAU])-(\d+)-(.+)$"
)
COMMIT_ENTITIES = {"目标": "goal", "AI任务": "ai", "用户任务": "user"}
COMMIT_PREFIXES = {"目标": "G", "AI任务": "A", "用户任务": "U"}
COMMIT_ACTIONS = {
    "登记": "create", "更新": "update", "启动": "start", "实现": "implement",
    "阻塞": "block", "恢复": "resume", "待验收": "submit", "验收修改": "revise",
    "完成": "complete", "取消": "cancel", "归档": "archive",
}


def _git_activity(service: GoGoalService, enabled: bool) -> dict:
    capability = git_capability(service.paths.root, enabled)
    if not enabled or not capability["available"] or not capability["repository"]:
        return {"capability": capability, "worktrees": [], "commits": []}
    try:
        process = subprocess.run(
            [capability["executable"], "log", "-100", "--format=%H%x1f%h%x1f%cI%x1f%s"],
            cwd=service.paths.root, text=True, capture_output=True, timeout=8, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return {"capability": capability, "worktrees": [], "commits": []}
    commits = []
    if process.returncode == 0:
        for line in process.stdout.splitlines():
            parts = line.split("\x1f", 3)
            match = COMMIT_RE.match(parts[3]) if len(parts) == 4 else None
            if match and match.group(3) == COMMIT_PREFIXES[match.group(1)]:
                commits.append({
                    "sha": parts[0], "shortSha": parts[1], "time": parts[2], "subject": parts[3],
                    "entity": COMMIT_ENTITIES[match.group(1)], "action": COMMIT_ACTIONS[match.group(2)],
                    "entityId": int(match.group(4)), "title": match.group(5),
                })
    worktrees: list[dict] = []
    try:
        worktree_process = subprocess.run(
            [capability["executable"], "worktree", "list", "--porcelain"],
            cwd=service.paths.root, text=True, capture_output=True, timeout=8, check=False,
        )
        if worktree_process.returncode == 0:
            current: dict[str, object] = {}
            for line in [*worktree_process.stdout.splitlines(), ""]:
                if not line:
                    if current:
                        worktrees.append(current)
                        current = {}
                    continue
                key, _, value = line.partition(" ")
                if key in ("bare", "detached"):
                    current[key] = True
                elif key in ("worktree", "HEAD", "branch", "locked", "prunable"):
                    current[key] = value or True
    except (OSError, subprocess.SubprocessError):
        worktrees = []
    return {"capability": capability, "worktrees": worktrees, "commits": commits}


class DashboardHandler(BaseHTTPRequestHandler):
    service: GoGoalService
    assets: Path

    def log_message(self, format: str, *args) -> None:
        return

    def _headers(self, status: HTTPStatus, content_type: str, length: int) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(length))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

    def _json(self, value: object, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = (json.dumps(value, ensure_ascii=False) + "\n").encode("utf-8")
        self._headers(status, "application/json; charset=utf-8", len(body))
        self.wfile.write(body)

    def _error(self, status: HTTPStatus, code: str) -> None:
        self._json({"error": code}, status)

    def do_POST(self) -> None:
        self._error(HTTPStatus.METHOD_NOT_ALLOWED, "readOnly")

    def do_PUT(self) -> None:
        self.do_POST()

    def do_DELETE(self) -> None:
        self.do_POST()

    def do_PATCH(self) -> None:
        self.do_POST()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/api/snapshot":
                with locked(self.service.paths):
                    state = self.service.state()
                    validation = validate_state(self.service.paths, state)
                config = state["config.json"]
                self._json({
                    "config": config,
                    "targets": state["target.json"]["targets"],
                    "targetArchive": state["target-archive.json"]["targets"],
                    "aiTasks": state["task.json"]["aiTasks"],
                    "userTasks": state["task.json"]["userTasks"],
                    "aiTaskArchive": state["task-archive.json"]["aiTasks"],
                    "userTaskArchive": state["task-archive.json"]["userTasks"],
                    "logs": state["log.json"]["logs"],
                    "validation": validation,
                    "updatedAt": local_time(),
                })
                return
            if parsed.path == "/api/document":
                relative = parse_qs(parsed.query).get("path", [""])[0]
                if not DOCUMENT_RE.fullmatch(relative):
                    self._error(HTTPStatus.BAD_REQUEST, "invalidDocumentPath")
                    return
                path = safe_document_path(self.service.paths, relative)
                if not path.is_file():
                    self._error(HTTPStatus.NOT_FOUND, "documentNotFound")
                    return
                self._json({"path": relative, "content": path.read_text(encoding="utf-8")})
                return
            if parsed.path == "/api/git":
                config = self.service.config_list()
                enabled = bool(config["git"]["enabled"] and config["dashboard"]["gitActivity"])
                self._json(_git_activity(self.service, enabled))
                return
            self._static(parsed.path)
        except (GoGoalError, OSError, UnicodeError):
            self._error(HTTPStatus.INTERNAL_SERVER_ERROR, "internal")

    def _static(self, request_path: str) -> None:
        name = "index.html" if request_path in ("", "/") else unquote(request_path).lstrip("/")
        candidate = (self.assets / name).resolve()
        try:
            candidate.relative_to(self.assets.resolve())
        except ValueError:
            self._error(HTTPStatus.NOT_FOUND, "resourceNotFound")
            return
        if not candidate.is_file():
            self._error(HTTPStatus.NOT_FOUND, "resourceNotFound")
            return
        body = candidate.read_bytes()
        content_type = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
        if content_type.startswith("text/") or content_type in ("application/javascript", "application/json"):
            content_type += "; charset=utf-8"
        self._headers(HTTPStatus.OK, content_type, len(body))
        self.wfile.write(body)


def serve(service: GoGoalService, host: str | None, port: int | None, open_browser: bool) -> None:
    config = service.config_list()["dashboard"]
    listen_host = host or config["host"]
    listen_port = port if port is not None else config["port"]
    if not isinstance(listen_port, int) or not 1 <= listen_port <= 65535:
        raise GoGoalError("看板端口必须是 1 到 65535 的整数。")
    assets = service.skill_root / "assets" / "dashboard"
    if not (assets / "index.html").is_file():
        raise GoGoalError("Skill 缺少看板前端资源。")
    handler = type("GoGoalDashboardHandler", (DashboardHandler,), {"service": service, "assets": assets})
    server_type = type(
        "GoGoalHTTPServer", (ThreadingHTTPServer,),
        {"address_family": socket.AF_INET6 if ":" in listen_host else socket.AF_INET},
    )
    try:
        server = server_type((listen_host, listen_port), handler)
    except OSError as exc:
        raise GoGoalError(f"无法监听 {listen_host}:{listen_port}，请检查端口或配置。") from exc
    url_host = "127.0.0.1" if listen_host == "0.0.0.0" else "::1" if listen_host == "::" else listen_host
    url_host = f"[{url_host}]" if ":" in url_host else url_host
    url = f"http://{url_host}:{server.server_port}/"
    locale = service.config_list()["locale"]
    print(ui(locale, "dashboard_url", url=url))
    print(ui(locale, "dashboard_stop"))
    if open_browser or config["autoOpen"]:
        webbrowser.open(url)
    try:
        server.serve_forever(poll_interval=0.25)
    finally:
        server.server_close()
