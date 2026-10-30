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
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any


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
                ],
            }
        )
    )


if __name__ == "__main__":
    main()
