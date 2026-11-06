"""Register independent plan, Memory, preflight and output operations."""

from token_io_decoupling_core.binding import BindingProvider
from token_io_decoupling_core.materialization_models import MaterializeDecoupledOutputPayload
from token_io_decoupling_tools.capabilities import capability_report
from token_io_decoupling_tools.compliance_preflight import (
    CompliancePreflightService,
    validate_decoupling_compliance,
)
from token_io_decoupling_tools.output_materialization import OutputMaterializationService
from token_io_decoupling_tools.payloads import _COMPLIANCE_PREFLIGHT
from token_io_decoupling_tools.serena_memory import SerenaMemoryReadService
from token_io_decoupling_tools.serena_memory_tools import register_serena_memory_tools
from token_io_decoupling_tools.task_plan_core import TaskPlanService
from token_io_decoupling_tools.task_plan_payloads import (
    TaskPlanArchivePayload,
    TaskPlanCompletePayload,
    TaskPlanUpdatePayload,
)
from token_io_decoupling_transport.registration import ToolRegistrar


def register_local_tools(
    registrar: ToolRegistrar,
    *,
    provider: BindingProvider,
    task_plan_service: TaskPlanService,
    serena_memory_service: SerenaMemoryReadService,
    compliance_service: CompliancePreflightService | None,
    output_materializer: OutputMaterializationService | None,
    output_materialization_details: dict[str, str],
) -> None:
    register_serena_memory_tools(registrar, serena_memory_service)
    registrar.register_no_args(
        "tools_capabilities",
        lambda: capability_report(
            provider,
            task_plan_service=task_plan_service,
            serena_memory_service=serena_memory_service,
            compliance_service=compliance_service,
            output_materialization=output_materialization_details,
        ),
    )
    for name, payload_type, callback in (
        ("task_plan_update", TaskPlanUpdatePayload, task_plan_service.update),
        ("task_plan_complete", TaskPlanCompletePayload, task_plan_service.complete),
        ("task_plan_archive", TaskPlanArchivePayload, task_plan_service.archive),
    ):
        registrar.register(
            name,
            payload_type,
            lambda payload, operation=callback: operation(payload.request.model_dump(mode="json")),
            enhanced=False,
        )
    registrar.register(
        "validate_decoupling_compliance",
        _COMPLIANCE_PREFLIGHT,
        lambda payload: validate_decoupling_compliance(compliance_service, payload.request),
        enhanced=False,
    )

    def materialize_output(payload):
        if output_materializer is None:
            return {
                "status": "unavailable",
                "reason_code": "trusted_authorization_context_unavailable",
            }
        return output_materializer.execute(
            payload.request, expected_binding=provider.current_binding()
        )

    registrar.register(
        "materialize_decoupled_output",
        MaterializeDecoupledOutputPayload,
        materialize_output,
        role="worker",
    )
