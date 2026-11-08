"""本地任务计划、Memory 和物化工具的定义与注册。"""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field

from token_io_decoupling_core.binding import BindingProvider
from token_io_decoupling_core.materialization_models import MaterializeDecoupledOutputPayload
from token_io_decoupling_tools.capabilities import capability_report
from token_io_decoupling_tools.compliance.service import (
    CompliancePreflightService,
    validate_decoupling_compliance,
)
from token_io_decoupling_tools.materialization.service import OutputMaterializationService
from token_io_decoupling_tools.payloads import _COMPLIANCE_PREFLIGHT
from token_io_decoupling_tools.serena_memory import SerenaMemoryReadService
from token_io_decoupling_tools.task_plan_payloads import (
    TaskPlanArchivePayload,
    TaskPlanCompletePayload,
    TaskPlanUpdatePayload,
)
from token_io_decoupling_tools.task_plans.service import TaskPlanService
from token_io_decoupling_transport.tool import ToolDefinition, ToolRegistrar

from .annotations import _MEMORY_READ
from .upstream import _UPSTREAM_TOOLS

MemoryPath = Annotated[
    str,
    Field(
        strict=True,
        min_length=1,
        max_length=4096,
        description=(
            "启动目录所绑定项目的 .serena/memories 下的相对名称，可带 mem: 前缀和 .md 后缀。"
        ),
    ),
]


TailLines = Annotated[
    int,
    Field(
        strict=True,
        ge=0,
        le=10000,
        description="最后 N 个逻辑行；零表示仅返回行数元数据，内容为空。",
    ),
]


ChangedContent = Annotated[
    str,
    Field(
        strict=True,
        min_length=1,
        max_length=64000,
        description="在尾部按字面查找的非空文本；不规范化，也不使用正则表达式。",
    ),
]


def register_tools(
    registrar: ToolRegistrar,
    *,
    provider: BindingProvider,
    task_plan_service: TaskPlanService,
    serena_memory_service: SerenaMemoryReadService,
    compliance_service: CompliancePreflightService | None,
    output_materializer: OutputMaterializationService | None,
    output_materialization_details: dict[str, str],
) -> None:
    """使用同一注册模板公开独立操作；注册关系不要求 workflow 调用顺序。"""

    def tools_capabilities() -> dict[str, Any]:
        return capability_report(
            provider,
            task_plan_service=task_plan_service,
            serena_memory_service=serena_memory_service,
            compliance_service=compliance_service,
            output_materialization=output_materialization_details,
        )

    def tail_read(memory_path: MemoryPath, tail_lines: TailLines) -> dict[str, Any]:
        return serena_memory_service.tail_read(memory_path, tail_lines)

    def write_check(
        memory_path: MemoryPath, changed_content: ChangedContent, tail_lines: TailLines
    ) -> dict[str, Any]:
        return serena_memory_service.write_check(memory_path, changed_content, tail_lines)

    def materialize_output(payload: MaterializeDecoupledOutputPayload) -> dict[str, Any]:
        if output_materializer is None:
            return {
                "status": "unavailable",
                "reason_code": "trusted_authorization_context_unavailable",
            }
        return output_materializer.execute(
            payload.request, expected_binding=provider.current_binding()
        )

    registrar.register_all(
        (
            ToolDefinition(
                name="tools_capabilities",
                callback=tools_capabilities,
                bounded_errors=True,
            ),
            ToolDefinition(
                name="serena_memory_tail_read",
                callback=tail_read,
                annotations=_MEMORY_READ,
            ),
            ToolDefinition(
                name="serena_memory_write_check",
                callback=write_check,
                annotations=_MEMORY_READ,
            ),
            ToolDefinition(
                name="task_plan_update",
                callback=lambda payload: task_plan_service.update(
                    payload.request.model_dump(mode="json")
                ),
                payload_type=TaskPlanUpdatePayload,
            ),
            ToolDefinition(
                name="task_plan_complete",
                callback=lambda payload: task_plan_service.complete(
                    payload.request.model_dump(mode="json")
                ),
                payload_type=TaskPlanCompletePayload,
            ),
            ToolDefinition(
                name="task_plan_archive",
                callback=lambda payload: task_plan_service.archive(
                    payload.request.model_dump(mode="json")
                ),
                payload_type=TaskPlanArchivePayload,
            ),
            ToolDefinition(
                name="validate_decoupling_compliance",
                callback=lambda payload: validate_decoupling_compliance(
                    compliance_service, payload.request
                ),
                payload_type=_COMPLIANCE_PREFLIGHT,
            ),
            ToolDefinition(
                name="materialize_decoupled_output",
                callback=materialize_output,
                payload_type=MaterializeDecoupledOutputPayload,
                role="worker",
                codex_guard=True,
            ),
            *_UPSTREAM_TOOLS,
        )
    )
