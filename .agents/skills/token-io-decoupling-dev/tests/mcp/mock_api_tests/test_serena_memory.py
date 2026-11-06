from __future__ import annotations

import builtins
from collections.abc import Mapping, Sequence
from pathlib import Path
from unittest.mock import patch

import pytest

from token_io_decoupling_tools.serena_memory import (
    MAX_CONTENT_CHARS,
    MAX_TAIL_LINES,
    SerenaMemoryReadService,
)


def _project(root: Path) -> Path:
    memories = root / ".serena" / "memories"
    memories.mkdir(parents=True)
    return memories


def test_reads_utf8_tail_and_preserves_lf_crlf_and_final_newline(tmp_path: Path) -> None:
    memories = _project(tmp_path)
    (memories / "notes.md").write_bytes("一行\r\n二行\n尾行".encode())
    service = SerenaMemoryReadService(tmp_path)

    result = service.tail_read("mem:notes.md", 2)

    assert result["status"] == "available"
    assert result["memory_name"] == "notes"
    assert result["content"] == "二行\n尾行"
    assert (result["total_lines"], result["returned_lines"]) == (3, 2)
    assert (result["start_line"], result["end_line"]) == (2, 3)
    assert result["ends_with_newline"] is False


def test_handles_empty_file_and_zero_line_window(tmp_path: Path) -> None:
    memories = _project(tmp_path)
    (memories / "empty.md").write_text("", encoding="utf-8")
    (memories / "notes.md").write_text("a\nb\n", encoding="utf-8")
    service = SerenaMemoryReadService(tmp_path)

    empty = service.tail_read("empty", 4)
    zero = service.tail_read("notes", 0)

    assert empty["status"] == "available"
    assert empty["content"] == "" and empty["total_lines"] == 0
    assert zero["status"] == "available"
    assert zero["content"] == "" and zero["total_lines"] == 2
    assert zero["returned_lines"] == 0
    assert zero["start_line"] is None and zero["end_line"] is None


def test_resolves_nested_logical_name_and_optional_md_suffix(tmp_path: Path) -> None:
    memories = _project(tmp_path)
    nested = memories / "plans" / "today.md"
    nested.parent.mkdir()
    nested.write_text("目标\n", encoding="utf-8")
    service = SerenaMemoryReadService(tmp_path)

    assert service.tail_read("plans/today", 1)["content"] == "目标\n"
    assert service.tail_read("mem:plans/today.md", 1)["memory_name"] == "plans/today"


def test_preserves_dots_in_logical_name_and_resolved_path(tmp_path: Path) -> None:
    memories = _project(tmp_path)
    target = memories / "foo.v1.md"
    target.write_text("v1\n", encoding="utf-8")
    service = SerenaMemoryReadService(tmp_path)

    result = service.tail_read("foo.v1", 1)

    assert result["status"] == "available"
    assert result["memory_name"] == "foo.v1"
    assert result["resolved_path"] == str(target)
    assert result["content"] == "v1\n"


def test_same_memory_name_isolated_by_each_startup_cwd(tmp_path: Path) -> None:
    project_a = tmp_path / "project-a"
    project_b = tmp_path / "project-b"
    memory_a = _project(project_a) / "notes.md"
    memory_b = _project(project_b) / "notes.md"
    memory_a.write_text("项目A\n", encoding="utf-8")
    memory_b.write_text("项目B\n", encoding="utf-8")

    result_a = SerenaMemoryReadService(project_a).tail_read("notes", 1)
    result_b = SerenaMemoryReadService(project_b).tail_read("notes", 1)

    assert result_a["content"] == "项目A\n"
    assert result_b["content"] == "项目B\n"
    assert result_a["resolved_path"] != result_b["resolved_path"]


def test_reads_only_under_startup_project_without_serena_or_subprocess_imports(
    tmp_path: Path,
) -> None:
    memories = _project(tmp_path)
    (memories / "notes.md").write_text("本地\n", encoding="utf-8")
    service = SerenaMemoryReadService(tmp_path)
    original_import = builtins.__import__

    def guarded_import(
        name: str,
        globals: Mapping[str, object] | None = None,
        locals: Mapping[str, object] | None = None,
        fromlist: Sequence[str] | None = (),
        level: int = 0,
    ) -> object:
        if name == "serena" or name.startswith("serena.") or name == "subprocess":
            raise AssertionError(f"unexpected local-program dependency: {name}")
        return original_import(name, globals, locals, fromlist, level)

    with patch("builtins.__import__", side_effect=guarded_import):
        assert service.tail_read("notes", 1)["content"] == "本地\n"
        assert service.write_check("notes", "本地", 1)["success"] is True


def test_write_check_is_case_sensitive_literal_and_does_not_echo_text(tmp_path: Path) -> None:
    memories = _project(tmp_path)
    (memories / "notes.md").write_text("append\nExact [x].\n", encoding="utf-8")
    service = SerenaMemoryReadService(tmp_path)

    matched = service.write_check("notes", "Exact [x].", 1)
    missed = service.write_check("notes", "exact [x].", 1)

    assert matched["success"] is True
    assert matched["reason_code"] == "memory_tail_match"
    assert "Exact [x]." not in matched
    assert missed["success"] is False
    assert missed["reason_code"] == "memory_tail_no_match"


@pytest.mark.parametrize(
    "reference",
    [
        "../outside",
        "nested/../../outside",
        "/tmp/outside.md",
        "C:/outside.md",
        r"C:\\outside.md",
        r"\\server\share\outside.md",
        "global/shared",
        "mem:",
        "nested//name",
        "nested:stream",
    ],
)
def test_rejects_traversal_absolute_global_and_windows_references(
    tmp_path: Path, reference: str
) -> None:
    _project(tmp_path)
    result = SerenaMemoryReadService(tmp_path).tail_read(reference, 1)
    assert result["status"] == "unavailable"
    assert result["reason_code"] == "memory_path_invalid"


def test_missing_project_memory_and_file_are_unavailable_without_creation(tmp_path: Path) -> None:
    service = SerenaMemoryReadService(tmp_path)
    assert service.capability()["status"] == "unavailable"
    result = service.tail_read("missing", 1)
    assert result["status"] == "unavailable"
    assert not (tmp_path / ".serena").exists()

    memories = _project(tmp_path)
    missing = SerenaMemoryReadService(tmp_path).tail_read("missing", 1)
    assert missing["reason_code"] == "memory_not_found"
    assert not list(memories.iterdir())


def test_rejects_symlinked_memory_path(tmp_path: Path) -> None:
    memories = _project(tmp_path)
    outside = tmp_path / "outside.md"
    outside.write_text("secret\n", encoding="utf-8")
    (memories / "linked.md").symlink_to(outside)

    result = SerenaMemoryReadService(tmp_path).tail_read("linked", 1)

    assert result["status"] == "unavailable"
    assert result["reason_code"] == "memory_symlink_rejected"


def test_rejects_memory_root_replaced_by_symlink_after_startup(tmp_path: Path) -> None:
    memory_root = _project(tmp_path)
    (memory_root / "notes.md").write_text("local\n", encoding="utf-8")
    service = SerenaMemoryReadService(tmp_path)
    other = tmp_path / "other" / ".serena" / "memories"
    other.mkdir(parents=True)
    (other / "notes.md").write_text("other project\n", encoding="utf-8")
    original_serena = tmp_path / ".serena"
    parked_serena = tmp_path / ".serena-original"
    original_serena.rename(parked_serena)
    original_serena.symlink_to(other.parent)

    result = service.tail_read("notes", 1)

    assert result["status"] == "unavailable"
    assert result["reason_code"] == "memory_symlink_rejected"
    assert result["content"] == ""


def test_enforces_windows_style_path_rules_without_claiming_windows_execution(
    tmp_path: Path,
) -> None:
    _project(tmp_path)
    for value in ("C:/notes.md", r"C:\notes.md", r"\\host\share\notes.md"):
        result = SerenaMemoryReadService(tmp_path).tail_read(value, 1)
        assert result["status"] == "unavailable"


def test_limits_tail_content_and_window_but_accepts_large_prefix(tmp_path: Path) -> None:
    memories = _project(tmp_path)
    (memories / "large-window.md").write_text("x" * (MAX_CONTENT_CHARS + 1), encoding="utf-8")
    (memories / "large-prefix.md").write_text("prefix\n" * 600_000 + "tail\n", encoding="utf-8")
    service = SerenaMemoryReadService(tmp_path)

    assert service.tail_read("large-window", 1)["reason_code"] == "memory_tail_too_large"
    prefix = service.tail_read("large-prefix", 1)
    assert prefix["status"] == "available"
    assert prefix["total_lines"] == 600_001
    assert prefix["content"] == "tail\n"
    assert (
        service.tail_read("large-window", MAX_TAIL_LINES + 1)["reason_code"] == "tail_lines_invalid"
    )
