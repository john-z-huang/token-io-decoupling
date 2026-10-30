from __future__ import annotations

import asyncio
import json
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from mcp import Client
from mcp.types import TextContent
from token_io_decoupling_workflow.task_plan_core import SerenaMemoryStore, TaskPlanService

from token_io_decoupling.server import create_server


class _ProtocolStore(SerenaMemoryStore):
    def __init__(self, project_root: str) -> None:
        self.project_root = project_root
        self.plans: dict[str, bytes] = {}
        self.archives: dict[str, bytes] = {}

    def capability(self) -> dict[str, object]:
        return {
            "status": "configured",
            "reason_code": "test_protocol_store",
            "project_root": self.project_root,
            "storage_scope": "project",
            "repository_id": None,
            "namespace": "plans/PLAN-<plan_id>",
            "archive_namespace": "archive-plans/PLAN-<plan_id>",
        }

    @contextmanager
    def locked(self, plan_id: str) -> Generator[None, None, None]:
        del plan_id
        yield

    def read(self, plan_id: str, *, archived: bool = False) -> bytes | None:
        collection = self.archives if archived else self.plans
        return collection.get(plan_id)

    def write(
        self, plan_id: str, expected: bytes | None, content: bytes
    ) -> tuple[str, bytes | None]:
        current = self.plans.get(plan_id)
        if current != expected:
            return "conflict", current
        self.plans[plan_id] = content
        return "written", content

    def archive(self, plan_id: str, expected: bytes) -> tuple[str, bytes | None]:
        current = self.plans.get(plan_id)
        if current is None or current != expected:
            return "conflict", current
        if plan_id in self.archives:
            return "collision", current
        self.archives[plan_id] = current
        del self.plans[plan_id]
        return "archived", current


def _record(record_id: str, kind: str, *, outcome: str | None = None) -> dict[str, object]:
    return {
        "record_id": record_id,
        "kind": kind,
        "text": f"Protocol evidence for {record_id}.",
        "sources": ["test requirement"],
        "outcome": outcome,
        "resolves_blocker_id": None,
        "supersedes_id": None,
        "supersedes_reason": None,
    }


def _receipt(result: Any) -> dict[str, Any]:
    assert not result.is_error
    assert result.content
    content = result.content[0]
    assert isinstance(content, TextContent)
    return json.loads(content.text or "{}")


def _resolve_schema_reference(root: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
    while "$ref" in schema:
        reference = schema["$ref"]
        assert isinstance(reference, str) and reference.startswith("#/")
        current: Any = root
        for segment in reference[2:].split("/"):
            current = current[segment]
        assert isinstance(current, dict)
        schema = current
    return schema


def test_task_plan_tools_negotiate_schema_default_and_configured_protocol(tmp_path: Path) -> None:
    project_root = str(tmp_path.resolve())

    async def run() -> None:
        default_server = create_server()
        async with Client(default_server, mode="auto") as client:
            listed = await client.list_tools()
            tools = {tool.name: tool for tool in listed.tools}
            names = {"task_plan_update", "task_plan_complete", "task_plan_archive"}
            assert names <= tools.keys()
            update_schema = tools["task_plan_update"].model_dump(by_alias=True)["inputSchema"]
            assert set(update_schema["properties"]) == {"payload"}
            payload_schema = _resolve_schema_reference(
                update_schema, update_schema["properties"]["payload"]
            )
            assert payload_schema["required"] == ["request"]
            request_schema = _resolve_schema_reference(
                update_schema, payload_schema["properties"]["request"]
            )
            assert set(request_schema["required"]) == {
                "project_root",
                "plan_id",
                "expected_revision",
                "request_id",
                "records",
            }
            assert set(request_schema["properties"]) == set(request_schema["required"])
            unavailable = _receipt(
                await client.call_tool(
                    "task_plan_update",
                    {
                        "payload": {
                            "request": {
                                "project_root": project_root,
                                "plan_id": "protocol-plan",
                                "expected_revision": None,
                                "request_id": "op-default",
                                "records": [_record("goal-1", "goal")],
                            }
                        }
                    },
                )
            )
            assert unavailable["status"] == "unavailable"
            assert unavailable["reason"] == "task_plan_backend_not_configured"
            assert unavailable["storage_scope"] is None
            assert unavailable["repository_id"] is None

        store = _ProtocolStore(project_root)
        configured_server = create_server(task_plan_service=TaskPlanService(store))
        async with Client(configured_server, mode="auto") as client:
            update = _receipt(
                await client.call_tool(
                    "task_plan_update",
                    {
                        "payload": {
                            "request": {
                                "project_root": project_root,
                                "plan_id": "protocol-plan",
                                "expected_revision": None,
                                "request_id": "op-create",
                                "records": [
                                    _record("criterion-1", "criterion"),
                                    _record("verification-1", "verification", outcome="passed"),
                                ],
                            }
                        }
                    },
                )
            )
            assert update["status"] == "updated"
            assert update["project_root"] == project_root
            assert update["memory_name"] == "plans/PLAN-protocol-plan"
            assert update["storage_scope"] == "project"
            assert update["repository_id"] is None
            revision = update["current_revision"]

            completed = _receipt(
                await client.call_tool(
                    "task_plan_complete",
                    {
                        "payload": {
                            "request": {
                                "project_root": project_root,
                                "plan_id": "protocol-plan",
                                "expected_revision": revision,
                                "request_id": "op-complete",
                                "criterion_evidence": [
                                    {
                                        "criterion_id": "criterion-1",
                                        "verification_id": "verification-1",
                                    }
                                ],
                                "records": [_record("result-1", "result")],
                            }
                        }
                    },
                )
            )
            assert completed["status"] == "completed"
            assert completed["plan_state"] == "completed"
            revision = completed["current_revision"]

            archived = _receipt(
                await client.call_tool(
                    "task_plan_archive",
                    {
                        "payload": {
                            "request": {
                                "project_root": project_root,
                                "plan_id": "protocol-plan",
                                "expected_revision": revision,
                            }
                        }
                    },
                )
            )
            assert archived["status"] == "archived"
            assert archived["memory_name"] == "archive-plans/PLAN-protocol-plan"
            assert archived["storage_scope"] == "project"
            assert archived["repository_id"] is None
            assert store.plans == {}
            assert "protocol-plan" in store.archives

    asyncio.run(run())
