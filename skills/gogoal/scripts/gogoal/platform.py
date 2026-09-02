"""跨平台锁、时间和 Git 能力探测。"""

from __future__ import annotations

import os
import shutil
import subprocess
from contextlib import AbstractContextManager
from datetime import datetime
from pathlib import Path

from .errors import GoGoalError


def local_time() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


class FileLock(AbstractContextManager["FileLock"]):
    def __init__(self, path: Path) -> None:
        self.path = path
        self.handle = None

    def __enter__(self) -> "FileLock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.handle = self.path.open("a+b")
        try:
            if os.name == "nt":
                import msvcrt

                self.handle.seek(0)
                if self.handle.read(1) == b"":
                    self.handle.write(b"0")
                    self.handle.flush()
                self.handle.seek(0)
                msvcrt.locking(self.handle.fileno(), msvcrt.LK_LOCK, 1)
            else:
                import fcntl

                fcntl.flock(self.handle.fileno(), fcntl.LOCK_EX)
        except OSError as exc:
            self.handle.close()
            self.handle = None
            raise GoGoalError("无法获取 GoGoal 管理文件锁。") from exc
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        if self.handle is None:
            return
        try:
            if os.name == "nt":
                import msvcrt

                self.handle.seek(0)
                msvcrt.locking(self.handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(self.handle.fileno(), fcntl.LOCK_UN)
        finally:
            self.handle.close()


def git_capability(project_root: Path, enabled: bool = True) -> dict:
    result = {
        "available": False, "repository": False, "worktree": False,
        "executable": None, "version": None, "branch": None,
    }
    if not enabled:
        return result
    executable = shutil.which("git")
    result["executable"] = executable
    if not executable:
        return result
    try:
        version_check = subprocess.run(
            [executable, "--version"], cwd=project_root,
            text=True, capture_output=True, timeout=5, check=False,
        )
        if version_check.returncode != 0:
            return result
        result["available"] = True
        result["version"] = version_check.stdout.strip() or None
        root_check = subprocess.run(
            [executable, "rev-parse", "--show-toplevel"], cwd=project_root,
            text=True, capture_output=True, timeout=5, check=False,
        )
        if root_check.returncode != 0:
            return result
        result["repository"] = True
        branch_check = subprocess.run(
            [executable, "branch", "--show-current"], cwd=project_root,
            text=True, capture_output=True, timeout=5, check=False,
        )
        if branch_check.returncode == 0:
            result["branch"] = branch_check.stdout.strip() or None
        worktree_check = subprocess.run(
            [executable, "worktree", "list", "--porcelain"], cwd=project_root,
            text=True, capture_output=True, timeout=5, check=False,
        )
        result["worktree"] = worktree_check.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return result
    return result
