"""Explicit, offline smoke with a real Serena installation and temporary Memories only.

Not collected by pytest. Run with an existing Serena project's interpreter via uv --no-sync.
The isolated process selects a temporary SERENA_HOME before importing any Serena module.
"""

from __future__ import annotations

import importlib
import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="serena-tail-smoke-") as temporary:
        root = Path(temporary).resolve()
        os.environ["SERENA_HOME"] = str(root / "serena-home")
        manager_module: Any = importlib.import_module("serena.memories.memory_manager")
        manager_type = manager_module.MemoryManager
        project = root / "project"
        project.mkdir()
        manager = manager_type(
            project / "custom-data",
            read_only_memory_patterns=[r"readonly/.*"],
            ignored_memory_patterns=[r"hidden/.*"],
        )
        project_memories = Path(manager._project_memory_dir)
        global_memories = Path(manager._global_memory_dir)
        assert project_memories.is_relative_to(root) and global_memories.is_relative_to(root)

        source = (
            Path(__file__).resolve().parents[2]
            / "packages/token_io_decoupling_workflow/src"
            / "token_io_decoupling_workflow/serena_memory.py"
        )
        spec = importlib.util.spec_from_file_location("serena_tail_real_smoke", source)
        assert spec is not None and spec.loader is not None
        module: Any = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        reader = module.SerenaMemoryReadService(manager, project)
        assert reader.capability()["status"] == "configured"

        manager.save_memory("notes/log", "旧记录\n新增记录\n", is_tool_context=True)
        path = project_memories / "notes/log.md"
        for reference in (
            "mem:notes/log",
            "notes/log.md",
            str(path.relative_to(project)),
            str(path),
        ):
            tail = reader.tail_read(reference, 1)
            assert tail["status"] == "available" and tail["content"] == "新增记录\n"
            assert tail["total_lines"] == 2 and tail["ends_with_newline"] is True
            assert reader.write_check(reference, "新增记录\n", 1)["success"] is True
        assert reader.write_check("notes/log", "旧记录", 1)["success"] is False
        assert reader.tail_read("notes/log", 0)["content"] == ""

        manager.save_memory("global/shared", "global data\n", is_tool_context=True)
        assert reader.tail_read("mem:global/shared", 1)["content"] == "global data\n"
        for name in ("readonly/pinned", "hidden/secret"):
            fixture = project_memories / f"{name}.md"
            fixture.parent.mkdir(exist_ok=True)
            fixture.write_text("fixture\n", encoding="utf-8")
        assert reader.tail_read("readonly/pinned", 1)["status"] == "available"
        assert reader.tail_read("hidden/secret", 1)["status"] != "available"
        outside = project / "ordinary.md"
        outside.write_text("outside\n", encoding="utf-8")
        assert reader.tail_read(str(outside), 1)["status"] != "available"
        link = project_memories / "alias.md"
        link.symlink_to(path)
        assert reader.tail_read("alias", 1)["status"] != "available"
        print(json.dumps({"status": "passed", "backend": "real_serena", "scope": "temporary_only"}))


if __name__ == "__main__":
    main()
