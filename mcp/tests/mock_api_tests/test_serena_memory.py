from __future__ import annotations

import os
import re
import sys
import types
from pathlib import Path

import pytest
from token_io_decoupling_workflow import serena_memory
from token_io_decoupling_workflow.serena_memory import SerenaMemoryReadService


class FakeMemoryManager:
    def __init__(self, project_memory_dir: Path | None, global_memory_dir: Path) -> None:
        self._project_memory_dir = project_memory_dir
        self._global_memory_dir = global_memory_dir
        self._encoding = "utf-8"
        self.ignored: list[re.Pattern[str]] = []
        self.read_only: list[re.Pattern[str]] = []
        self.checked: list[str] = []

    @staticmethod
    def _sanitize_name(name: str) -> str:
        name = name.removeprefix("mem:")
        if name.endswith(".md"):
            name = name[:-3]
        return name.replace(os.sep, "/")

    def _check_not_ignored(self, name: str) -> None:
        self.checked.append(name)
        if any(pattern.fullmatch(name) for pattern in self.ignored):
            raise ValueError("ignored")


@pytest.fixture
def service_factory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    module = types.ModuleType("serena.memories.memory_manager")
    module.__dict__["MemoryManager"] = FakeMemoryManager
    monkeypatch.setitem(sys.modules, "serena.memories.memory_manager", module)

    def make(*, custom_root: Path | None = None):
        project = tmp_path / "project"
        project.mkdir(exist_ok=True)
        project_root = custom_root or project / "configured" / "memories"
        project_root.mkdir(parents=True, exist_ok=True)
        global_root = tmp_path / "serena-home" / "memories" / "global"
        global_root.mkdir(parents=True, exist_ok=True)
        manager = FakeMemoryManager(project_root, global_root)
        return (
            SerenaMemoryReadService(manager, project),
            manager,
            project,
            project_root,
            global_root,
        )

    return make


def test_unconfigured_service_is_unavailable_without_creating_files(tmp_path: Path):
    service = SerenaMemoryReadService()

    assert service.capability()["status"] == "unavailable"
    assert service.capability()["reason_code"] == "serena_memory_backend_not_configured"
    assert service.tail_read("mem:plan", 2)["reason_code"] == "serena_memory_backend_not_configured"
    assert list(tmp_path.iterdir()) == []


def test_accepts_memory_reference_bare_name_and_project_relative_entity_path(service_factory):
    service, _, project, root, _ = service_factory()
    content = "first\nselected\nlast"
    (root / "area").mkdir()
    target = root / "area" / "notes.md"
    target.write_text(content, encoding="utf-8")

    for memory_path in (
        "mem:area/notes",
        "area/notes.md",
        str(target.relative_to(project)),
        str(target),
    ):
        result = service.tail_read(memory_path, 2)
        assert result["status"] == "available"
        assert result["memory_name"] == "area/notes"
        assert result["content"] == "selected\nlast"
        assert result["total_lines"] == 3
        assert (result["start_line"], result["end_line"]) == (2, 3)


def test_global_reference_and_absolute_global_path_are_supported(service_factory):
    service, _, _, _, global_root = service_factory()
    target = global_root / "team" / "plan.md"
    target.parent.mkdir()
    target.write_text("shared", encoding="utf-8")

    for memory_path in ("mem:global/team/plan.md", str(target)):
        result = service.tail_read(memory_path, 1)
        assert result["status"] == "available"
        assert result["memory_name"] == "global/team/plan"
        assert result["content"] == "shared"


def test_optional_md_normalization_matches_serena_suffix_behavior(service_factory):
    service, manager, _, root, _ = service_factory()
    target = root / "double.md.md"
    target.write_text("double suffix", encoding="utf-8")
    manager.ignored.append(re.compile(r"double\.md"))

    assert service.tail_read("mem:double.md.md", 1)["reason_code"] == "memory_ignored_or_invalid"
    manager.ignored.clear()
    result = service.tail_read(str(target), 1)
    assert result["memory_name"] == "double.md"
    assert result["content"] == "double suffix"


def test_ignored_is_blocked_but_read_only_memory_is_readable(service_factory):
    service, manager, _, root, _ = service_factory()
    (root / "private.md").write_text("do not expose", encoding="utf-8")
    (root / "readonly.md").write_text("read permitted", encoding="utf-8")
    manager.ignored.append(re.compile(r"private"))
    manager.read_only.append(re.compile(r"readonly"))

    ignored = service.tail_read("private", 1)
    readable = service.tail_read("readonly", 1)
    assert ignored["status"] == "unavailable"
    assert ignored["reason_code"] == "memory_ignored_or_invalid"
    assert "do not expose" not in repr(ignored)
    assert readable["status"] == "available"
    assert readable["content"] == "read permitted"


@pytest.mark.parametrize(
    ("memory_path", "reason"),
    [
        ("../outside.md", "memory_path_invalid"),
        ("mem:../outside", "memory_path_invalid"),
        ("/etc/passwd", "memory_path_outside_memory_roots"),
        ("global", "memory_scope_unavailable_or_invalid"),
    ],
)
def test_rejects_traversal_and_out_of_scope_paths(service_factory, memory_path, reason):
    service, _, _, _, _ = service_factory()

    result = service.tail_read(memory_path, 1)

    assert result["status"] == "unavailable"
    assert result["reason_code"] == reason


def test_rejects_non_markdown_entity_path(service_factory):
    service, _, _, root, _ = service_factory()
    target = root / "notes.txt"
    target.write_text("text", encoding="utf-8")

    result = service.tail_read(str(target), 1)

    assert result["reason_code"] == "memory_path_not_markdown"


def test_missing_directory_and_non_regular_file_return_bounded_errors(service_factory):
    service, _, _, root, _ = service_factory()
    missing = service.tail_read("missing", 2)
    (root / "folder.md").mkdir()
    directory = service.tail_read("folder", 2)

    assert missing["reason_code"] == "memory_not_found"
    assert directory["reason_code"] == "memory_file_not_regular"
    assert "content" not in directory or directory["content"] == ""


def test_invalid_encoding_fails_without_returning_partial_content(service_factory):
    service, manager, _, root, _ = service_factory()
    (root / "invalid.md").write_bytes(b"\xff\xfe")

    result = service.tail_read("invalid", 1)

    assert result["reason_code"] == "memory_encoding_invalid"
    assert result["content"] == ""


@pytest.mark.parametrize(
    ("raw", "expected", "lines", "tail_lines"),
    [
        (b"", "", 0, 10),
        (b"one\ntwo\n", "two\n", 2, 1),
        (b"one\r\ntwo\r\n", "two\r\n", 2, 1),
        ("café\n最後".encode(), "café\n最後", 2, 2),
        (b"one\n\n", "one\n\n", 2, 2),
        (b"one", "one", 1, 1),
        (b"\n", "\n", 1, 1),
    ],
)
def test_tail_line_semantics(service_factory, raw, expected, lines, tail_lines):
    service, _, _, root, _ = service_factory()
    (root / "sample.md").write_bytes(raw)

    result = service.tail_read("sample", tail_lines)

    assert result["status"] == "available"
    assert result["content"] == expected
    assert result["total_lines"] == lines
    assert result["returned_lines"] == min(tail_lines, lines)


@pytest.mark.parametrize(
    ("raw", "changed"), [(b"old\nnew\n", "new\n"), (b"old\r\nnew\r\n", "new\r\n")]
)
def test_write_check_preserves_exact_line_terminators(service_factory, raw, changed):
    service, _, _, root, _ = service_factory()
    (root / "sample.md").write_bytes(raw)

    result = service.write_check("sample", changed, 1)

    assert result["success"] is True


def test_oversized_tail_fails_but_a_large_older_line_can_leave_the_window(service_factory):
    service, _, _, root, _ = service_factory()
    (root / "too-large.md").write_text("abcdef\n" * 10_000, encoding="utf-8")
    (root / "recover.md").write_text("x" * 64_001 + "\n" + "z\n" * 10_000, encoding="utf-8")

    oversized = service.tail_read("too-large", 10_000)
    recovered = service.tail_read("recover", 10_000)

    assert oversized["reason_code"] == "memory_tail_too_large"
    assert recovered["status"] == "available"
    assert recovered["total_lines"] == 10_001
    assert len(recovered["content"]) == 20_000


@pytest.mark.parametrize("tail_lines", [-1, True, 10_001, 1.0, "2"])
def test_rejects_invalid_tail_window(service_factory, tail_lines):
    service, _, _, _, _ = service_factory()

    assert service.tail_read("sample", tail_lines)["reason_code"] == "tail_lines_invalid"


def test_zero_tail_returns_counts_without_content(service_factory):
    service, _, _, root, _ = service_factory()
    (root / "sample.md").write_text("one\ntwo\n", encoding="utf-8")

    result = service.tail_read("sample", 0)

    assert result["status"] == "available"
    assert result["total_lines"] == 2
    assert result["returned_lines"] == 0
    assert result["start_line"] is None
    assert result["content"] == ""


def test_reports_missing_final_newline_when_append_can_extend_same_line(service_factory):
    service, _, _, root, _ = service_factory()
    target = root / "sample.md"
    target.write_text("old", encoding="utf-8")

    before = service.tail_read("sample", 1)
    with target.open("a", encoding="utf-8") as stream:
        stream.write("-append")
    after = service.tail_read("sample", 1)

    assert before["total_lines"] == after["total_lines"] == 1
    assert before["ends_with_newline"] is False
    assert after["ends_with_newline"] is False
    assert after["content"] == "old-append"


def test_write_check_matches_only_the_requested_current_tail_and_does_not_echo_text(
    service_factory,
):
    service, _, _, root, _ = service_factory()
    (root / "sample.md").write_text("old\nnew note", encoding="utf-8")

    matched = service.write_check("sample", "new note", 1)
    too_short = service.write_check("sample", "old", 1)
    historical = service.write_check("sample", "old", 2)

    assert matched["success"] is True
    assert matched["match_scope"] == "current_tail_content_only"
    assert matched["match_start"] == 0
    assert "new note" not in repr(matched)
    assert too_short["success"] is False
    assert too_short["reason_code"] == "memory_tail_no_match"
    assert historical["success"] is True


@pytest.mark.parametrize("changed_content", ["", 1, None])
def test_write_check_rejects_empty_or_non_string_content(service_factory, changed_content):
    service, _, _, _, _ = service_factory()

    result = service.write_check("sample", changed_content, 1)

    assert result["success"] is False
    assert result["reason_code"] == "changed_content_invalid"


def test_write_check_can_match_across_logical_lines(service_factory):
    service, _, _, root, _ = service_factory()
    (root / "sample.md").write_text("alpha\nbeta", encoding="utf-8")

    result = service.write_check("sample", "alpha\nbeta", 2)

    assert result["success"] is True
    assert result["match_start"] == 0
    assert result["match_end"] == len("alpha\nbeta")


def test_write_check_unavailable_is_false_and_does_not_expose_tail(service_factory):
    service, _, _, root, _ = service_factory()
    (root / "sample.md").write_text("sensitive tail", encoding="utf-8")

    result = service.write_check("sample", "absent", 1)

    assert result["success"] is False
    assert result["reason_code"] == "memory_tail_no_match"
    assert "sensitive tail" not in repr(result)


def test_rejects_symlinked_memory_file_and_directory_escape(service_factory, tmp_path: Path):
    service, _, _, root, _ = service_factory()
    outside = tmp_path / "outside.md"
    outside.write_text("secret", encoding="utf-8")
    (root / "linked.md").symlink_to(outside)
    (root / "linkdir").symlink_to(outside.parent, target_is_directory=True)

    file_result = service.tail_read("linked", 1)
    directory_result = service.tail_read("linkdir/outside", 1)

    assert file_result["reason_code"] == "memory_symlink_or_directory_rejected"
    assert directory_result["reason_code"] == "memory_symlink_or_directory_rejected"
    assert "secret" not in repr(file_result)


def test_detects_file_change_during_read(service_factory, monkeypatch: pytest.MonkeyPatch):
    service, _, _, root, _ = service_factory()
    target = root / "sample.md"
    target.write_text("before", encoding="utf-8")
    original_read = os.read
    changed = False

    def read_then_change(fd: int, size: int) -> bytes:
        nonlocal changed
        result = original_read(fd, size)
        if not changed and result:
            changed = True
            target.write_text("after!", encoding="utf-8")
        return result

    monkeypatch.setattr(serena_memory.os, "read", read_then_change)

    result = service.tail_read("sample", 1)

    assert result["reason_code"] == "memory_changed_during_read"
    assert result["content"] == ""


def test_detects_parent_directory_symlink_replacement_during_read(
    service_factory, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    service, _, _, root, _ = service_factory()
    parent = root / "nested"
    parent.mkdir()
    target = parent / "sample.md"
    target.write_text("content", encoding="utf-8")
    external = tmp_path / "external"
    external.mkdir()
    original_read = os.read
    changed = False

    def read_then_replace_parent(fd: int, size: int) -> bytes:
        nonlocal changed
        result = original_read(fd, size)
        if not changed and result:
            changed = True
            parent.rename(root / "nested-original")
            parent.symlink_to(external, target_is_directory=True)
        return result

    monkeypatch.setattr(serena_memory.os, "read", read_then_replace_parent)

    result = service.tail_read("nested/sample", 1)

    assert result["status"] == "unavailable"
    assert result["content"] == ""
    assert result["reason_code"] in {
        "memory_changed_during_read",
        "memory_symlink_or_directory_rejected",
    }


def test_rejects_manager_root_rebinding(service_factory, tmp_path: Path):
    service, manager, _, _, _ = service_factory()
    manager._project_memory_dir = tmp_path / "other"
    manager._project_memory_dir.mkdir()

    assert service.tail_read("sample", 1)["reason_code"] == "serena_memory_root_binding_changed"


def test_reports_unavailable_when_secure_open_primitives_are_missing(service_factory, monkeypatch):
    service, _, _, _, _ = service_factory()
    monkeypatch.setattr(service, "_secure_open_available", lambda: False)

    assert service.capability()["status"] == "unavailable"
    assert service.tail_read("sample", 1)["reason_code"] == "secure_dirfd_open_unsupported"
