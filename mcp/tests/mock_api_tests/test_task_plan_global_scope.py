from __future__ import annotations

import hashlib
import json
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import RLock
from types import SimpleNamespace
from typing import Any

import pytest
from token_io_decoupling_workflow import task_plan_core as core
from token_io_decoupling_workflow.task_plan_core import (
    _GIT_IDENTITY_DOMAIN,
    SerenaMemoryStore,
    TaskPlanFailure,
    TaskPlanService,
    _append_event,
    _request_hash,
)


def _git(
    checkout: Path,
    *arguments: str,
    env: dict[str, str],
) -> str:
    result = subprocess.run(
        ["git", "-C", str(checkout), *arguments],
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
        env=env,
    )
    return result.stdout.strip()


@pytest.fixture
def git_checkouts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Path]:
    for name in ("GIT_DIR", "GIT_COMMON_DIR", "GIT_WORK_TREE"):
        monkeypatch.delenv(name, raising=False)

    root = tmp_path / "git-fixtures"
    root.mkdir()
    empty_template = root / "empty-template"
    empty_template.mkdir()
    empty_hooks = root / "empty-hooks"
    empty_hooks.mkdir()
    global_config = root / "empty-gitconfig"
    global_config.write_text(
        f'[core]\n\thooksPath = "{empty_hooks}"\n[commit]\n\tgpgsign = false\n',
        encoding="utf-8",
    )
    env = os.environ.copy()
    env.update(
        {
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": str(global_config),
            "GIT_TERMINAL_PROMPT": "0",
        }
    )
    for name in tuple(env):
        if name.startswith(("GIT_CONFIG_KEY_", "GIT_CONFIG_VALUE_")) or name == "GIT_CONFIG_COUNT":
            env.pop(name)

    main = root / "main"
    main.mkdir()
    subprocess.run(
        ["git", "init", "--quiet", f"--template={empty_template}"],
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
        cwd=main,
        env=env,
    )
    _git(main, "config", "user.name", "Task Plan Test", env=env)
    _git(main, "config", "user.email", "task-plan@example.invalid", env=env)
    _git(main, "config", "commit.gpgsign", "false", env=env)
    _git(main, "config", "core.hooksPath", str(empty_hooks), env=env)
    (main / "README.md").write_text("temporary git fixture\n", encoding="utf-8")
    _git(main, "add", "README.md", env=env)
    _git(main, "commit", "--quiet", "-m", "fixture", env=env)

    worktree_one = root / "worktree-one"
    worktree_two = root / "worktree-two"
    _git(
        main, "worktree", "add", "--quiet", "-b", "fixture-one", str(worktree_one), "HEAD", env=env
    )
    _git(
        main, "worktree", "add", "--quiet", "-b", "fixture-two", str(worktree_two), "HEAD", env=env
    )

    independent = root / "independent"
    independent.mkdir()
    subprocess.run(
        ["git", "init", "--quiet", f"--template={empty_template}"],
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
        cwd=independent,
        env=env,
    )
    _git(independent, "config", "user.name", "Task Plan Test", env=env)
    _git(independent, "config", "user.email", "task-plan@example.invalid", env=env)
    _git(independent, "config", "commit.gpgsign", "false", env=env)
    _git(independent, "config", "core.hooksPath", str(empty_hooks), env=env)
    (independent / "README.md").write_text("independent temporary fixture\n", encoding="utf-8")
    _git(independent, "add", "README.md", env=env)
    _git(independent, "commit", "--quiet", "-m", "fixture", env=env)

    return {
        "main": main,
        "worktree_one": worktree_one,
        "worktree_two": worktree_two,
        "independent": independent,
        "root": root,
        "env_config": global_config,
        "empty_hooks": empty_hooks,
    }


class _GlobalFilesystemMemoryManager:
    def __init__(self, global_root: Path, project_root: Path) -> None:
        self._global_memory_dir = global_root
        self._project_memory_dir = project_root
        self.path_calls: list[str] = []
        self.policy_calls: list[tuple[str, bool]] = []
        self._guard = RLock()

    def _check_not_ignored(self, memory_name: str) -> None:
        self.policy_calls.append((memory_name, False))

    def _check_write_access(self, memory_name: str, write: bool) -> None:
        self.policy_calls.append((memory_name, write))

    def get_memory_file_path(self, memory_name: str) -> Path:
        self.path_calls.append(memory_name)
        if memory_name.startswith("global/"):
            root = self._global_memory_dir
            relative_name = memory_name.removeprefix("global/")
        else:
            root = self._project_memory_dir
            relative_name = memory_name
        path = root / f"{relative_name}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        return path


def _global_service(
    project_root: Path, manager: _GlobalFilesystemMemoryManager
) -> tuple[TaskPlanService, SerenaMemoryStore]:
    store = object.__new__(SerenaMemoryStore)
    store.project_root = str(project_root.resolve(strict=True))
    store.storage_scope = "global"
    store.repository_id = core._repository_id_for_checkout(store.project_root)
    store.memory_root = manager._global_memory_dir.resolve(strict=True)
    store._manager = manager
    return TaskPlanService(store), store


def _record(identifier: str, kind: str, *, outcome: str | None = None) -> dict[str, Any]:
    return {
        "record_id": identifier,
        "kind": kind,
        "text": f"Temporary repository isolation evidence for {identifier}.",
        "sources": ["test requirement"],
        "outcome": outcome,
        "resolves_blocker_id": None,
        "supersedes_id": None,
        "supersedes_reason": None,
    }


def _update(
    service: TaskPlanService,
    project_root: Path,
    plan_id: str,
    revision: str | None,
    request_id: str,
    *records: dict[str, Any],
) -> dict[str, Any]:
    return service.update(
        {
            "project_root": str(project_root.resolve()),
            "plan_id": plan_id,
            "expected_revision": revision,
            "request_id": request_id,
            "records": list(records),
        }
    )


def test_common_directory_identity_is_shared_by_worktrees_and_aliases(
    git_checkouts: dict[str, Path],
) -> None:
    main = git_checkouts["main"]
    one = git_checkouts["worktree_one"]
    two = git_checkouts["worktree_two"]
    alias = git_checkouts["root"] / "main-alias"
    alias.symlink_to(main, target_is_directory=True)

    identity = core._repository_id_for_checkout(main)
    common_dir = Path(
        _git(main, "rev-parse", "--path-format=absolute", "--git-common-dir", env=os.environ.copy())
    ).resolve()
    expected = (
        "git-v1-" + hashlib.sha256(_GIT_IDENTITY_DOMAIN + os.fsencode(str(common_dir))).hexdigest()
    )

    assert identity == expected
    assert core._repository_id_for_checkout(one) == identity
    assert core._repository_id_for_checkout(two) == identity
    assert core._repository_id_for_checkout(alias) == identity
    assert core._repository_id_for_checkout(git_checkouts["independent"]) != identity

    subdirectory = main / "subdirectory"
    subdirectory.mkdir()
    with pytest.raises(TaskPlanFailure, match="git_identity_output_invalid"):
        core._repository_id_for_checkout(subdirectory)


def test_store_keeps_project_default_and_requires_existing_global_root(
    git_checkouts: dict[str, Path],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    project_memory = tmp_path / "project-memory"
    project_memory.mkdir()
    missing_global_root = tmp_path / "global-memory-missing"

    class _ConstructibleManager:
        _project_memory_dir = project_memory
        _global_memory_dir = missing_global_root

        def get_memory_file_path(self, memory_name: str) -> Path:
            return project_memory / f"{memory_name}.md"

        def _check_not_ignored(self, memory_name: str) -> None:
            del memory_name

        def _check_write_access(self, memory_name: str, write: bool) -> None:
            del memory_name, write

    monkeypatch.setattr(
        core.importlib,
        "import_module",
        lambda name: SimpleNamespace(MemoryManager=_ConstructibleManager),
    )
    manager = _ConstructibleManager()

    project_store = SerenaMemoryStore(manager, git_checkouts["main"])
    assert project_store.storage_scope == "project"
    assert project_store.repository_id is None

    with pytest.raises(TaskPlanFailure, match="serena_global_memory_unavailable"):
        SerenaMemoryStore(manager, git_checkouts["main"], storage_scope="global")

    missing_global_root.mkdir()
    manager._global_memory_dir = missing_global_root
    global_store = SerenaMemoryStore(manager, git_checkouts["main"], storage_scope="global")
    assert global_store.storage_scope == "global"
    assert global_store.repository_id == core._repository_id_for_checkout(git_checkouts["main"])


def test_global_lifecycle_shares_revisions_replay_and_archive_across_worktrees(
    git_checkouts: dict[str, Path], tmp_path: Path
) -> None:
    global_root = tmp_path / "serena-global"
    global_root.mkdir()
    manager = _GlobalFilesystemMemoryManager(global_root, tmp_path / "unused-project-memory")
    main_service, main_store = _global_service(git_checkouts["main"], manager)
    one_service, one_store = _global_service(git_checkouts["worktree_one"], manager)
    two_service, two_store = _global_service(git_checkouts["worktree_two"], manager)
    assert main_store.repository_id == one_store.repository_id == two_store.repository_id

    initial_request = {
        "project_root": main_store.project_root,
        "plan_id": "shared-plan",
        "expected_revision": None,
        "request_id": "create-shared",
        "records": [
            _record("goal-1", "goal"),
            _record("criterion-1", "criterion"),
            _record("verification-1", "verification", outcome="passed"),
        ],
    }
    created = main_service.update(initial_request)
    assert created["status"] == "updated"
    assert created["storage_scope"] == "global"
    assert created["repository_id"] == main_store.repository_id
    assert created["project_root"] == main_store.project_root
    assert created["memory_name"] == (
        f"global/token-io-decoupling/repos/{main_store.repository_id}/plans/PLAN-shared-plan"
    )
    active = main_store._fixed_path("shared-plan", False)
    first_bytes = active.read_bytes()
    assert b"~~~json task-plan-header-v2\n" in first_bytes
    assert b"~~~json task-plan-event-v2\n" in first_bytes
    marker = first_bytes.index(core._HEADER_V2_PREFIX)
    line_end = first_bytes.index(core._HEADER_SUFFIX, marker)
    header = json.loads(
        first_bytes[marker + len(core._HEADER_V2_PREFIX) : line_end].decode("utf-8")
    )
    assert header["repository_id"] == main_store.repository_id
    assert "project_root" not in header
    parsed = core._parse_snapshot(
        first_bytes, "shared-plan", repository_id=main_store.repository_id
    )
    assert parsed.events[0]["repository_id"] == main_store.repository_id
    assert "project_root" not in parsed.events[0]

    replay_request = {**initial_request, "project_root": one_store.project_root}
    replayed = one_service.update(replay_request)
    assert replayed["status"] == "replayed"
    assert replayed["project_root"] == one_store.project_root
    assert replayed["current_revision"] == created["current_revision"]
    assert active.read_bytes() == first_bytes

    changed = _update(
        two_service,
        git_checkouts["worktree_two"],
        "shared-plan",
        created["current_revision"],
        "worktree-two-progress",
        _record("progress-1", "progress"),
    )
    assert changed["status"] == "updated"
    assert changed["current_revision"] != created["current_revision"]
    changed_bytes = active.read_bytes()
    stale = _update(
        main_service,
        git_checkouts["main"],
        "shared-plan",
        created["current_revision"],
        "stale-main-write",
        _record("stale-fact", "fact"),
    )
    assert stale["status"] == "conflict"
    assert stale["reason"] == "stale_revision"
    assert active.read_bytes() == changed_bytes

    completed = two_service.complete(
        {
            "project_root": two_store.project_root,
            "plan_id": "shared-plan",
            "expected_revision": changed["current_revision"],
            "request_id": "complete-shared",
            "criterion_evidence": [
                {"criterion_id": "criterion-1", "verification_id": "verification-1"}
            ],
            "records": [_record("result-1", "result")],
        }
    )
    assert completed["status"] == "completed"
    completed_bytes = active.read_bytes()
    archived = main_service.archive(
        {
            "project_root": main_store.project_root,
            "plan_id": "shared-plan",
            "expected_revision": completed["current_revision"],
        }
    )
    assert archived["status"] == "archived"
    archive_path = main_store._fixed_path("shared-plan", True)
    assert archive_path.read_bytes() == completed_bytes
    assert archive_path.is_file()
    assert not active.exists()
    assert archived["memory_name"] == (
        f"global/token-io-decoupling/repos/{main_store.repository_id}/"
        "archive-plans/PLAN-shared-plan"
    )
    assert (
        two_service.archive(
            {
                "project_root": two_store.project_root,
                "plan_id": "shared-plan",
                "expected_revision": completed["current_revision"],
            }
        )["status"]
        == "already_archived"
    )

    concurrent_seed = _update(
        main_service,
        git_checkouts["main"],
        "concurrent-plan",
        None,
        "concurrent-create",
        _record("goal-concurrent", "goal"),
    )
    assert concurrent_seed["status"] == "updated"
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(
                lambda pair: _update(
                    pair[0],
                    pair[1],
                    "concurrent-plan",
                    concurrent_seed["current_revision"],
                    f"concurrent-{pair[1].name}",
                    _record(f"fact-{pair[1].name}", "fact"),
                ),
                (
                    (one_service, git_checkouts["worktree_one"]),
                    (two_service, git_checkouts["worktree_two"]),
                ),
            )
        )
    assert sorted(result["status"] for result in results) == ["conflict", "updated"]


def test_same_plan_id_isolated_between_independent_repositories_and_old_global_data_is_untouched(
    git_checkouts: dict[str, Path], tmp_path: Path
) -> None:
    global_root = tmp_path / "serena-global"
    global_root.mkdir()
    manager = _GlobalFilesystemMemoryManager(global_root, tmp_path / "unused-project-memory")
    main_service, main_store = _global_service(git_checkouts["main"], manager)
    other_service, other_store = _global_service(git_checkouts["independent"], manager)
    assert main_store.repository_id != other_store.repository_id

    unscoped = manager.get_memory_file_path("global/plans/PLAN-isolated")
    unscoped_bytes = b"Old unscoped global plan; must stay untouched.\n"
    unscoped.write_bytes(unscoped_bytes)
    common_request = {
        "plan_id": "isolated",
        "expected_revision": None,
        "request_id": "same-operation",
        "records": [_record("same-goal", "goal")],
    }
    main_result = main_service.update({**common_request, "project_root": main_store.project_root})
    other_result = other_service.update(
        {**common_request, "project_root": other_store.project_root}
    )

    assert main_result["status"] == other_result["status"] == "updated"
    assert main_result["current_revision"] != other_result["current_revision"]
    main_active = main_store._fixed_path("isolated", False)
    other_active = other_store._fixed_path("isolated", False)
    assert main_active != other_active
    assert main_store.repository_id is not None
    assert other_store.repository_id is not None
    assert main_store.repository_id.encode() in main_active.read_bytes()
    assert other_store.repository_id.encode() in other_active.read_bytes()
    assert unscoped.read_bytes() == unscoped_bytes


@pytest.mark.parametrize(
    ("components", "archived"),
    [
        (("token-io-decoupling",), False),
        (("token-io-decoupling", "repos"), False),
        (("token-io-decoupling", "repos", "REPOSITORY_ID"), False),
        (("token-io-decoupling", "repos", "REPOSITORY_ID", "plans"), False),
        (("token-io-decoupling", "repos", "REPOSITORY_ID", "archive-plans"), True),
    ],
)
def test_global_storage_rejects_symlinks_in_each_namespace_layer_before_effect(
    git_checkouts: dict[str, Path],
    tmp_path: Path,
    components: tuple[str, ...],
    archived: bool,
) -> None:
    global_root = tmp_path / "serena-global"
    global_root.mkdir()
    manager = _GlobalFilesystemMemoryManager(global_root, tmp_path / "unused-project-memory")
    service, store = _global_service(git_checkouts["main"], manager)
    repository_id = store.repository_id
    assert repository_id is not None
    segments = tuple(repository_id if value == "REPOSITORY_ID" else value for value in components)
    link = global_root.joinpath(*segments)
    link.parent.mkdir(parents=True, exist_ok=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    link.symlink_to(outside, target_is_directory=True)

    result = service.update(
        {
            "project_root": store.project_root,
            "plan_id": "symlink-plan",
            "expected_revision": None,
            "request_id": "symlink-update",
            "records": [_record("goal-symlink", "goal")],
        }
    )

    assert result["status"] == "unavailable"
    assert result["reason"] == "memory_namespace_symlink_rejected"
    assert manager.path_calls == []
    assert not (global_root / ".token-io-task-plan.lock").exists()
    if archived:
        assert store._fixed_path("symlink-plan", True).parent.is_symlink()


def test_global_scope_rejects_wrong_checkout_and_revalidates_backend_before_memory_effects(
    git_checkouts: dict[str, Path], tmp_path: Path
) -> None:
    global_root = tmp_path / "serena-global"
    global_root.mkdir()
    manager = _GlobalFilesystemMemoryManager(global_root, tmp_path / "unused-project-memory")
    service, store = _global_service(git_checkouts["main"], manager)

    wrong_root = service.update(
        {
            "project_root": str(git_checkouts["independent"].resolve()),
            "plan_id": "root-mismatch",
            "expected_revision": None,
            "request_id": "wrong-root",
            "records": [_record("goal-wrong-root", "goal")],
        }
    )
    assert wrong_root["status"] == "conflict"
    assert wrong_root["reason"] == "project_scope_mismatch"
    assert manager.path_calls == []
    assert not (global_root / ".token-io-task-plan.lock").exists()

    manager._global_memory_dir = tmp_path / "missing-global-root"
    unavailable = _update(
        service,
        git_checkouts["main"],
        "root-changed",
        None,
        "root-changed",
        _record("goal-root-changed", "goal"),
    )
    assert unavailable["status"] == "unavailable"
    assert unavailable["reason"] == "serena_global_memory_unavailable"
    assert service.capability()["status"] == "unavailable"
    assert manager.path_calls == []


def test_global_scope_rejects_repository_identity_change_before_memory_effects(
    git_checkouts: dict[str, Path], tmp_path: Path
) -> None:
    global_root = tmp_path / "serena-global"
    global_root.mkdir()
    manager = _GlobalFilesystemMemoryManager(global_root, tmp_path / "unused-project-memory")
    service, store = _global_service(git_checkouts["worktree_one"], manager)
    fixture_env = os.environ.copy()
    fixture_env.update(
        {
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": str(git_checkouts["env_config"]),
            "GIT_TERMINAL_PROMPT": "0",
        }
    )

    _git(
        git_checkouts["main"],
        "worktree",
        "remove",
        "--force",
        str(git_checkouts["worktree_one"]),
        env=fixture_env,
    )
    _git(
        git_checkouts["independent"],
        "worktree",
        "add",
        "--quiet",
        "-b",
        "replacement-checkout",
        str(git_checkouts["worktree_one"]),
        "HEAD",
        env=fixture_env,
    )

    capability = service.capability()
    assert capability["status"] == "unavailable"
    assert capability["reason_code"] == "repository_identity_changed"
    result = _update(
        service,
        git_checkouts["worktree_one"],
        "identity-changed",
        None,
        "identity-changed",
        _record("goal-identity-changed", "goal"),
    )
    assert result["status"] == "unavailable"
    assert result["reason"] == "repository_identity_changed"
    assert manager.path_calls == []
    assert not (global_root / ".token-io-task-plan.lock").exists()


@pytest.mark.parametrize("redirect_variable", ["GIT_DIR", "GIT_COMMON_DIR", "GIT_WORK_TREE"])
def test_global_identity_rejects_git_redirect_environment(
    git_checkouts: dict[str, Path],
    monkeypatch: pytest.MonkeyPatch,
    redirect_variable: str,
) -> None:
    monkeypatch.setenv(redirect_variable, str(git_checkouts["independent"]))
    with pytest.raises(TaskPlanFailure, match="git_environment_redirected"):
        core._repository_id_for_checkout(git_checkouts["main"])


def test_global_history_rejects_project_v1_without_migrating_its_bytes(
    git_checkouts: dict[str, Path], tmp_path: Path
) -> None:
    global_root = tmp_path / "serena-global"
    global_root.mkdir()
    manager = _GlobalFilesystemMemoryManager(global_root, tmp_path / "unused-project-memory")
    service, store = _global_service(git_checkouts["main"], manager)
    plan_id = "legacy-global"
    data = {"records": [_record("goal-v1", "goal")]}
    request_hash = _request_hash(plan_id, store.project_root, "update", data)
    v1_bytes = _append_event(
        None,
        plan_id,
        store.project_root,
        "old-v1-operation",
        "update",
        request_hash,
        data,
    )
    target = store._fixed_path(plan_id, False)
    target.parent.mkdir(parents=True)
    target.write_bytes(v1_bytes)

    rejected = _update(
        service,
        git_checkouts["main"],
        plan_id,
        hashlib.sha256(v1_bytes).hexdigest(),
        "new-global-operation",
        _record("goal-v2", "goal"),
    )

    assert rejected["status"] == "blocked"
    assert rejected["reason"] == "history_identity_mismatch"
    assert target.read_bytes() == v1_bytes
