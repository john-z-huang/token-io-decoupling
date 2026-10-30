"""Explicit local integration smoke in an interpreter already containing Serena.

This is not collected by ordinary pytest and performs no network/configuration calls.
All memories and the project root are temporary. No mocks or user memories are used.
"""

from __future__ import annotations

import hashlib
import importlib
import importlib.metadata
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any


def _git(checkout: Path, *arguments: str, env: dict[str, str]) -> str:
    result = subprocess.run(
        ["git", "-C", str(checkout), *arguments],
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
        env=env,
    )
    return result.stdout.strip()


def _make_git_fixtures(root: Path) -> dict[str, Path]:
    root.mkdir(exist_ok=True)
    template = root / "empty-template"
    template.mkdir()
    hooks = root / "empty-hooks"
    hooks.mkdir()
    git_config = root / "isolated-gitconfig"
    git_config.write_text("", encoding="utf-8")
    env = os.environ.copy()
    env.update(
        {
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": str(git_config),
            "GIT_TERMINAL_PROMPT": "0",
        }
    )
    for name in ("GIT_DIR", "GIT_COMMON_DIR", "GIT_WORK_TREE", "GIT_CONFIG_COUNT"):
        env.pop(name, None)
    for name in tuple(env):
        if name.startswith(("GIT_CONFIG_KEY_", "GIT_CONFIG_VALUE_")):
            env.pop(name)

    def init_repo(path: Path, contents: str) -> None:
        path.mkdir()
        subprocess.run(
            ["git", "init", "--quiet", f"--template={template}"],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
            cwd=path,
            env=env,
        )
        _git(path, "config", "user.name", "Task Plan Smoke", env=env)
        _git(path, "config", "user.email", "task-plan-smoke@example.invalid", env=env)
        _git(path, "config", "commit.gpgsign", "false", env=env)
        _git(path, "config", "core.hooksPath", str(hooks), env=env)
        (path / "README.md").write_text(contents, encoding="utf-8")
        _git(path, "add", "README.md", env=env)
        _git(path, "commit", "--quiet", "-m", "temporary smoke fixture", env=env)

    main = root / "repo-main"
    init_repo(main, "Temporary repository shared by worktrees.\n")
    worktree_one = root / "repo-worktree-one"
    worktree_two = root / "repo-worktree-two"
    _git(
        main,
        "worktree",
        "add",
        "--quiet",
        "-b",
        "smoke-one",
        str(worktree_one),
        "HEAD",
        env=env,
    )
    _git(
        main,
        "worktree",
        "add",
        "--quiet",
        "-b",
        "smoke-two",
        str(worktree_two),
        "HEAD",
        env=env,
    )
    independent = root / "repo-independent"
    init_repo(independent, "Independent temporary repository.\n")
    return {
        "main": main,
        "worktree_one": worktree_one,
        "worktree_two": worktree_two,
        "independent": independent,
    }


def main() -> None:
    memory_manager_type = importlib.import_module("serena.memories.memory_manager").MemoryManager

    workspace = Path(__file__).resolve().parents[2]
    source = (
        workspace
        / "packages/token_io_decoupling_workflow/src/token_io_decoupling_workflow/task_plan_core.py"
    )
    spec = importlib.util.spec_from_file_location("task_plan_real_serena_smoke", source)
    if spec is None or spec.loader is None:
        raise RuntimeError("task-plan source unavailable")
    core = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = core
    spec.loader.exec_module(core)

    def record(identifier: str, kind: str, text: str, **fields: Any) -> dict[str, Any]:
        return {
            "record_id": identifier,
            "kind": kind,
            "text": text,
            "sources": ["synthetic:real-serena-smoke"],
            "outcome": None,
            "resolves_blocker_id": None,
            "supersedes_id": None,
            "supersedes_reason": None,
            **fields,
        }

    with tempfile.TemporaryDirectory(prefix="task-plan-real-serena-") as temporary:
        root = Path(temporary)
        project = root / "project"
        project.mkdir()
        manager = memory_manager_type(root / "canonical-data")
        global_root = root / "canonical-global-data"
        global_root.mkdir()
        manager._global_memory_dir = global_root
        store = core.SerenaMemoryStore(manager, project)
        service = core.TaskPlanService(store)
        project_root = str(project.resolve())
        plan_id = "real-smoke"
        active = manager.get_memory_file_path(f"plans/PLAN-{plan_id}")
        legacy = (
            "目标：保留历史\r\n两份清单已核验\r\n未发现 PR 模板\r\n`mem:plans/PLAN-real-smoke`\r\n"
        ).encode()
        active.write_bytes(legacy)
        sentinel = manager.get_memory_file_path("archive-plans/PLAN-sentinel")
        sentinel_bytes = b"Existing sentinel: `mem:plans/PLAN-real-smoke`\n"
        sentinel.write_bytes(sentinel_bytes)

        def update(
            instance: Any, identifier: str, revision: str | None, request_id: str, *records: Any
        ) -> dict[str, Any]:
            return instance.update(
                {
                    "project_root": project_root,
                    "plan_id": identifier,
                    "expected_revision": revision,
                    "request_id": request_id,
                    "records": list(records),
                }
            )

        created = update(
            service,
            plan_id,
            hashlib.sha256(legacy).hexdigest(),
            "adopt",
            record("goal", "goal", "Retain all previous records"),
            record("criterion", "criterion", "History remains traceable"),
            record("old-fact", "fact", "Initial assumption: template exists"),
            record("peer", "fact", "Synthetic peer: two manifests verified"),
            record("failed", "verification", "First check failed", outcome="failed"),
            record("blocker", "blocker", "A passing verification is needed"),
        )
        assert created["status"] == "updated", created
        assert active.read_bytes().startswith(legacy)
        revision = created["current_revision"]
        changed = update(
            service,
            plan_id,
            revision,
            "stage-two",
            record(
                "new-fact",
                "fact",
                "Inspection found no template",
                supersedes_id="old-fact",
                supersedes_reason="Inspection supersedes the initial assumption",
            ),
            record("passed", "verification", "Second check passed", outcome="passed"),
            record(
                "resolution", "resolution", "Passing check recorded", resolves_blocker_id="blocker"
            ),
        )
        assert changed["status"] == "updated", changed
        before_complete = active.read_bytes()
        stale = update(service, plan_id, revision, "stale", record("stale", "fact", "No write"))
        assert stale["status"] == "conflict", stale
        assert active.read_bytes() == before_complete
        completion_request = {
            "project_root": project_root,
            "plan_id": plan_id,
            "expected_revision": changed["current_revision"],
            "request_id": "complete",
            "criterion_evidence": [{"criterion_id": "criterion", "verification_id": "passed"}],
            "records": [
                record("result", "result", "Original and superseding records retained"),
                record("limit", "limitation", "Synthetic evidence; no claim about truth"),
            ],
        }
        completed = service.complete(completion_request)
        assert completed["status"] == "completed", completed
        final = active.read_bytes()
        assert final.startswith(before_complete)
        assert b"Initial assumption: template exists" in final
        assert b"Inspection found no template" in final
        assert b"<!--" not in final
        archive_request = {
            "project_root": project_root,
            "plan_id": plan_id,
            "expected_revision": completed["current_revision"],
        }
        archived = service.archive(archive_request)
        assert archived["status"] == "archived", archived
        archive = manager.get_memory_file_path(f"archive-plans/PLAN-{plan_id}")
        assert archive.read_bytes() == final and not active.exists()
        assert sentinel.read_bytes() == sentinel_bytes
        assert "Inspection found no template" in manager.load_memory(
            f"archive-plans/PLAN-{plan_id}"
        )
        assert service.archive(archive_request)["replayed"] is True
        assert service.complete(completion_request)["replayed"] is True
        resurrected = update(service, plan_id, None, "resurrect", record("x", "goal", "Rejected"))
        assert resurrected["status"] == "conflict" and not active.exists()
        assert archive.read_bytes() == final

        # Two independently configured stores participate in the same file lock.
        second = core.TaskPlanService(core.SerenaMemoryStore(manager, project))
        initial = update(service, "concurrent", None, "create", record("g", "goal", "Concurrency"))
        assert initial["status"] == "updated", initial
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [
                pool.submit(
                    update,
                    instance,
                    "concurrent",
                    initial["current_revision"],
                    f"writer-{index}",
                    record(f"f-{index}", "fact", f"Writer {index}"),
                )
                for index, instance in enumerate((service, second))
            ]
            statuses = sorted(future.result()["status"] for future in futures)
        assert statuses == ["conflict", "updated"], statuses

        restricted = memory_manager_type(
            root / "canonical-data", read_only_memory_patterns=["plans/PLAN-denied"]
        )
        denied_service = core.TaskPlanService(core.SerenaMemoryStore(restricted, project))
        denied = update(denied_service, "denied", None, "denied", record("g", "goal", "No write"))
        assert denied["status"] not in {"updated", "replayed"}, denied
        assert not (store.memory_root / "plans/PLAN-denied.md").exists()

        git_projects = _make_git_fixtures(root / "git-fixtures")
        global_main = core.TaskPlanService(
            core.SerenaMemoryStore(manager, git_projects["main"], storage_scope="global")
        )
        global_one = core.TaskPlanService(
            core.SerenaMemoryStore(manager, git_projects["worktree_one"], storage_scope="global")
        )
        global_two = core.TaskPlanService(
            core.SerenaMemoryStore(manager, git_projects["worktree_two"], storage_scope="global")
        )
        global_independent = core.TaskPlanService(
            core.SerenaMemoryStore(manager, git_projects["independent"], storage_scope="global")
        )
        global_main_store = global_main._store
        global_one_store = global_one._store
        global_two_store = global_two._store
        assert global_main_store.repository_id == global_one_store.repository_id
        assert global_main_store.repository_id == global_two_store.repository_id
        assert global_main_store.repository_id != global_independent._store.repository_id
        global_main_root = global_main_store.project_root
        global_one_root = global_one_store.project_root
        global_two_root = global_two_store.project_root

        def update_global(
            instance: Any,
            current_root: str,
            identifier: str,
            revision: str | None,
            request_id: str,
            *records: Any,
        ) -> dict[str, Any]:
            return instance.update(
                {
                    "project_root": current_root,
                    "plan_id": identifier,
                    "expected_revision": revision,
                    "request_id": request_id,
                    "records": list(records),
                }
            )

        global_plan_id = "global-smoke"
        global_records = [
            record("global-goal", "goal", "Share this plan across linked worktrees"),
            record("global-criterion", "criterion", "Every worktree sees the same revision"),
            record(
                "global-verification",
                "verification",
                "Temporary linked worktrees share the active plan",
                outcome="passed",
            ),
        ]
        global_created = update_global(
            global_main,
            global_main_root,
            global_plan_id,
            None,
            "global-create",
            *global_records,
        )
        assert global_created["status"] == "updated", global_created
        assert global_created["storage_scope"] == "global"
        assert global_created["repository_id"] == global_main_store.repository_id
        assert global_created["project_root"] == global_main_root
        global_active_name = (
            f"global/token-io-decoupling/repos/{global_main_store.repository_id}/"
            f"plans/PLAN-{global_plan_id}"
        )
        global_active = manager.get_memory_file_path(global_active_name)
        initial_global_bytes = global_active.read_bytes()
        assert b"~~~json task-plan-header-v2\n" in initial_global_bytes
        assert b"~~~json task-plan-event-v2\n" in initial_global_bytes
        global_snapshot = core._parse_snapshot(
            initial_global_bytes,
            global_plan_id,
            repository_id=global_main_store.repository_id,
        )
        assert global_snapshot.events[0]["repository_id"] == global_main_store.repository_id
        assert "project_root" not in global_snapshot.events[0]

        global_replay = update_global(
            global_one,
            global_one_root,
            global_plan_id,
            None,
            "global-create",
            *global_records,
        )
        assert global_replay["status"] == "replayed", global_replay
        assert global_replay["project_root"] == global_one_root
        assert global_replay["current_revision"] == global_created["current_revision"]
        assert global_active.read_bytes() == initial_global_bytes

        global_progress = update_global(
            global_two,
            global_two_root,
            global_plan_id,
            global_created["current_revision"],
            "global-progress",
            record("global-progress", "progress", "Updated from the second linked worktree"),
        )
        assert global_progress["status"] == "updated", global_progress
        global_completed = global_one.complete(
            {
                "project_root": global_one_root,
                "plan_id": global_plan_id,
                "expected_revision": global_progress["current_revision"],
                "request_id": "global-complete",
                "criterion_evidence": [
                    {
                        "criterion_id": "global-criterion",
                        "verification_id": "global-verification",
                    }
                ],
                "records": [record("global-result", "result", "Shared lifecycle completed")],
            }
        )
        assert global_completed["status"] == "completed", global_completed
        global_completed_bytes = global_active.read_bytes()
        global_archived = global_two.archive(
            {
                "project_root": global_two_root,
                "plan_id": global_plan_id,
                "expected_revision": global_completed["current_revision"],
            }
        )
        assert global_archived["status"] == "archived", global_archived
        global_archive_name = (
            f"global/token-io-decoupling/repos/{global_main_store.repository_id}/"
            f"archive-plans/PLAN-{global_plan_id}"
        )
        global_archive = manager.get_memory_file_path(global_archive_name)
        assert global_archive.read_bytes() == global_completed_bytes
        assert not global_active.exists()
        assert "Shared lifecycle completed" in manager.load_memory(global_archive_name)
        assert (
            global_main.archive(
                {
                    "project_root": global_main_root,
                    "plan_id": global_plan_id,
                    "expected_revision": global_completed["current_revision"],
                }
            )["status"]
            == "already_archived"
        )

        old_unscoped_name = "global/plans/PLAN-global-isolation"
        old_unscoped = manager.get_memory_file_path(old_unscoped_name)
        old_unscoped_bytes = b"Old unscoped plan, preserved byte-for-byte.\n"
        old_unscoped.write_bytes(old_unscoped_bytes)
        same_named_plan = "global-isolation"
        main_isolated_records = [record("isolated-goal", "goal", "Primary repository data")]
        independent_isolated_records = [
            record("isolated-goal", "goal", "Independent repository data")
        ]
        main_isolated = update_global(
            global_main,
            global_main_root,
            same_named_plan,
            None,
            "same-operation",
            *main_isolated_records,
        )
        other_isolated = update_global(
            global_independent,
            global_independent._store.project_root,
            same_named_plan,
            None,
            "same-operation",
            *independent_isolated_records,
        )
        assert main_isolated["status"] == other_isolated["status"] == "updated"
        assert main_isolated["current_revision"] != other_isolated["current_revision"]
        assert old_unscoped.read_bytes() == old_unscoped_bytes

        main_isolated_name = (
            f"global/token-io-decoupling/repos/{global_main_store.repository_id}/"
            f"plans/PLAN-{same_named_plan}"
        )
        independent_isolated_name = (
            f"global/token-io-decoupling/repos/{global_independent._store.repository_id}/"
            f"plans/PLAN-{same_named_plan}"
        )
        main_topic = f"token-io-decoupling/repos/{global_main_store.repository_id}/plans"
        independent_topic = (
            f"token-io-decoupling/repos/{global_independent._store.repository_id}/plans"
        )
        main_global_names = manager.list_global_memories(main_topic).get_full_list()
        independent_global_names = manager.list_global_memories(independent_topic).get_full_list()
        assert main_isolated_name in main_global_names
        assert independent_isolated_name not in main_global_names
        assert independent_isolated_name in independent_global_names
        assert main_isolated_name not in independent_global_names
        main_content = manager.load_memory(main_isolated_name)
        independent_content = manager.load_memory(independent_isolated_name)
        assert "Primary repository data" in main_content
        assert "Independent repository data" not in main_content
        assert "Independent repository data" in independent_content
        assert "Primary repository data" not in independent_content

        global_read_only_name = (
            f"global/token-io-decoupling/repos/{global_main_store.repository_id}/"
            "plans/PLAN-global-read-only"
        )
        read_only_global_root = root / "read-only-global-data"
        read_only_global_root.mkdir()
        read_only_global_manager = memory_manager_type(
            root / "read-only-canonical-data",
            read_only_memory_patterns=[global_read_only_name],
        )
        read_only_global_manager._global_memory_dir = read_only_global_root
        read_only_global_service = core.TaskPlanService(
            core.SerenaMemoryStore(
                read_only_global_manager,
                git_projects["main"],
                storage_scope="global",
            )
        )
        read_only_global_result = read_only_global_service.update(
            {
                "project_root": global_main_root,
                "plan_id": "global-read-only",
                "expected_revision": None,
                "request_id": "global-read-only",
                "records": [record("goal", "goal", "This write must be denied")],
            }
        )
        assert read_only_global_result["reason"] == "serena_memory_read_only", (
            read_only_global_result
        )
        assert not read_only_global_manager.get_memory_file_path(global_read_only_name).exists()

        global_ignored_name = (
            f"global/token-io-decoupling/repos/{global_main_store.repository_id}/"
            "plans/PLAN-global-ignored"
        )
        ignored_global_root = root / "ignored-global-data"
        ignored_global_root.mkdir()
        ignored_global_manager = memory_manager_type(
            root / "ignored-canonical-data",
            ignored_memory_patterns=[global_ignored_name],
        )
        ignored_global_manager._global_memory_dir = ignored_global_root
        ignored_global_service = core.TaskPlanService(
            core.SerenaMemoryStore(
                ignored_global_manager,
                git_projects["main"],
                storage_scope="global",
            )
        )
        ignored_global_result = ignored_global_service.update(
            {
                "project_root": global_main_root,
                "plan_id": "global-ignored",
                "expected_revision": None,
                "request_id": "global-ignored",
                "records": [record("goal", "goal", "This write must be denied")],
            }
        )
        assert ignored_global_result["reason"] == "serena_memory_ignored_or_invalid", (
            ignored_global_result
        )
        assert not ignored_global_manager.get_memory_file_path(global_ignored_name).exists()

    print(
        json.dumps(
            {
                "status": "passed",
                "backend": "actual installed Serena MemoryManager",
                "serena_version": importlib.metadata.version("serena-agent"),
                "scope": "temporary project and canonical data only",
                "checks": [
                    "legacy UTF-8/CRLF preservation",
                    "readable multi-stage records and explicit supersession",
                    "stale revision rejection",
                    "completion and exact-byte archive",
                    "no reference propagation to existing sentinel",
                    "archive/completion replay and no resurrection",
                    "two-store concurrency",
                    "native read-only policy",
                    "actual global linked-worktree sharing and independent-repository isolation",
                    "actual global topic-scoped list/load isolation",
                    "actual global read-only and ignored logical-name policy",
                ],
            }
        )
    )


if __name__ == "__main__":
    main()
