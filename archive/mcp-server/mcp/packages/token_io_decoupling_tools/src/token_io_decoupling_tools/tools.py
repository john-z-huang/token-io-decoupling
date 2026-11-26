"""Bind bounded utility callbacks to per-server services."""

from __future__ import annotations

from typing import Any

from token_io_decoupling_core.binding import BindingProvider
from token_io_decoupling_core.rules import DEFAULT_CONTEXT_TEXT_BUDGET, RuleLoader

from token_io_decoupling_tools.compliance_preflight import (
    CompliancePreflightService,
    validate_decoupling_compliance,
)
from token_io_decoupling_tools.output_materialization import OutputMaterializationService


def create_utility_callbacks(
    *,
    compliance_service: CompliancePreflightService | None,
    rules: RuleLoader,
    provider: BindingProvider,
    output_materializer: OutputMaterializationService | None = None,
) -> dict[str, Any]:

    def get_rule_context(payload: Any) -> Any:
        if payload.context_version is None:
            return rules.load_context(payload.node_id.value, language=payload.language)
        return rules.load_context_bundle(
            payload.node_id.value,
            language=payload.language,
            fragment_ids=payload.fragment_ids,
            max_chars=payload.max_chars or DEFAULT_CONTEXT_TEXT_BUDGET,
        )

    def materialize_output(payload: Any) -> Any:
        if output_materializer is None:
            return {
                "status": "unavailable",
                "reason_code": "trusted_authorization_context_unavailable",
            }
        return output_materializer.execute(
            payload.request, expected_binding=provider.current_binding()
        )

    return {
        "rules_get_context": get_rule_context,
        "validate_decoupling_compliance": lambda payload: validate_decoupling_compliance(
            compliance_service, payload.request
        ),
        "materialize_decoupled_output": materialize_output,
    }
