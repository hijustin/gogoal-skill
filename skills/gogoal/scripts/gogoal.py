#!/usr/bin/env python3
"""GoGoal CLI 唯一入口。"""

from __future__ import annotations

import sys
from pathlib import Path

MIN_VERSION = (3, 12)


def main() -> int:
    if sys.version_info < MIN_VERSION:
        current = ".".join(str(part) for part in sys.version_info[:3])
        print(
            f"GoGoal 需要 Python 3.12 或更高版本，当前为 {current}。"
            "请使用 python3.12、兼容的 python3/python，或 Windows 的 py -3.12。",
            file=sys.stderr,
        )
        return 2
    script_dir = Path(__file__).resolve().parent
    if str(script_dir) not in sys.path:
        sys.path.insert(0, str(script_dir))
    from gogoal.cli import run

    return run()


if __name__ == "__main__":
    raise SystemExit(main())
