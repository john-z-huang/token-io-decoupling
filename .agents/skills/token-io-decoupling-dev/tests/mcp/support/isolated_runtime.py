"""临时运行时进程与离线 wheel 安装；不向子进程传递 API 凭据。"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def runtime_environment() -> dict[str, str]:
    return {
        key: value
        for key, value in os.environ.items()
        if key not in {"OPENAI_API_KEY", "OPENAI_BASE_URL", "PYTHONPATH"}
    }


def run_runtime_probe(
    interpreter: str | Path,
    probe: str,
    project: Path,
    service: str,
    *,
    isolated: bool = False,
) -> subprocess.CompletedProcess[str]:
    command = [str(interpreter)]
    if isolated:
        command.append("-I")
    # 继续用 -c 启动，不把私有 support 目录自动加入隔离解释器的导入路径。
    command.extend(
        [
            "-c",
            "import runpy, sys; runpy.run_path(sys.argv.pop(1), run_name='__main__')",
            str(Path(__file__).with_name(probe)),
            service,
        ]
    )
    return subprocess.run(
        command,
        cwd=project,
        env=runtime_environment(),
        text=True,
        capture_output=True,
        timeout=45 if isolated else 30,
    )


def create_runtime_environment(environment: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["uv", "venv", "--offline", "--python", sys.executable, str(environment)],
        capture_output=True,
        text=True,
        check=False,
    )


def install_runtime_wheels(
    interpreter: Path, wheels: list[Path], project: Path
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["uv", "pip", "install", "--offline", "--python", str(interpreter), *map(str, wheels)],
        cwd=project,
        capture_output=True,
        text=True,
        check=False,
    )
