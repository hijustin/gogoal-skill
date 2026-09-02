"""项目定位、JSON 读取和受锁原子写入。"""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .constants import EMPTY_FILES, FORMAT_VERSION
from .errors import GoGoalError
from .platform import FileLock

JSON_FILES = ("config.json", *EMPTY_FILES.keys())


@dataclass(frozen=True)
class ProjectPaths:
    root: Path
    data: Path

    @classmethod
    def locate(cls, start: Path | None = None) -> "ProjectPaths":
        current = (start or Path.cwd()).resolve()
        for candidate in (current, *current.parents):
            data = candidate / "gogoal"
            if (data / "config.json").is_file():
                return cls(candidate, data)
        raise GoGoalError("未找到 gogoal/config.json；请在项目目录运行 gogoal init。")

    @classmethod
    def for_init(cls, root: Path | None = None) -> "ProjectPaths":
        project = (root or Path.cwd()).resolve()
        return cls(project, project / "gogoal")

    def file(self, name: str) -> Path:
        return self.data / name


def read_json(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError as exc:
        raise GoGoalError(f"缺少必需文件：{path.name}") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise GoGoalError(f"无法读取有效 JSON：{path.name}") from exc


def load_state(paths: ProjectPaths) -> dict[str, Any]:
    state = {name: read_json(paths.file(name)) for name in JSON_FILES}
    config = state["config.json"]
    if not isinstance(config, dict) or config.get("format") != FORMAT_VERSION:
        raise GoGoalError(f"不兼容的数据格式：仅支持 format={FORMAT_VERSION}，拒绝修改。")
    return state


def encode_json(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _replace_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink(missing_ok=True)


def write_payloads(paths: ProjectPaths, encoded_changes: dict[str, bytes]) -> None:
    """在单一回滚边界内替换多个文件，并核对写后字节。"""
    originals: dict[Path, bytes | None] = {}
    encoded: dict[Path, bytes] = {}
    for name, content in encoded_changes.items():
        path = paths.file(name)
        originals[path] = path.read_bytes() if path.exists() else None
        encoded[path] = content

    replaced: list[Path] = []
    try:
        for path, content in encoded.items():
            _replace_bytes(path, content)
            replaced.append(path)
        for path, content in encoded.items():
            if path.read_bytes() != content:
                raise OSError(f"write verification failed: {path.name}")
    except OSError as exc:
        for path in reversed(replaced):
            original = originals[path]
            try:
                if original is None:
                    path.unlink(missing_ok=True)
                else:
                    _replace_bytes(path, original)
            except OSError:
                pass
        raise GoGoalError("写入管理数据失败，已尝试恢复动作前状态。") from exc


def write_many(paths: ProjectPaths, changes: dict[str, Any]) -> None:
    encoded: dict[str, bytes] = {}
    for name, value in changes.items():
        content = encode_json(value)
        # 写入正式文件前验证编码结果仍是合法 JSON。
        json.loads(content.decode("utf-8"))
        encoded[name] = content
    write_payloads(paths, encoded)


def locked(paths: ProjectPaths) -> FileLock:
    return FileLock(paths.data / ".lock")


def safe_document_path(paths: ProjectPaths, relative: str) -> Path:
    candidate = (paths.data / relative).resolve()
    try:
        candidate.relative_to(paths.data.resolve())
    except ValueError as exc:
        raise GoGoalError("对象文档路径超出 gogoal/ 目录。") from exc
    return candidate
