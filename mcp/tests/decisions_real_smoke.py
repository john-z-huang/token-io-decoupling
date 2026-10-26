"""Opt-in, synthetic-only smoke for the enabled Decisions integration."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

from token_io_decoupling_core.binding import BindingError
from token_io_decoupling_core.models import CodingMode, ModeCount, SemanticRef
from token_io_decoupling_core.rules import RuleLoader
from token_io_decoupling_core.state_models import (
    BindingIdentity,
    CheckpointNode,
    HostCapability,
    HostGuard,
    SessionRole,
    VerifiedChildBinding,
    WorkflowOpenRequest,
)
from token_io_decoupling_state.service import StateService
from token_io_decoupling_workflow.decisions import (
    DecisionsAdvisor,
    DecisionsRuntimeConfig,
    TaskIntentInput,
)


class SyntheticProvider:
    def current_binding(self) -> BindingIdentity:
        return BindingIdentity(
            project_id="synthetic-decisions-smoke",
            root_session_id="synthetic-root",
            current_session_id="synthetic-root",
            role=SessionRole.PARENT,
            capabilities=frozenset(HostCapability),
            guards=frozenset(HostGuard),
        )

    def verify_child_binding(
        self, parent: BindingIdentity, child_session_id: str
    ) -> VerifiedChildBinding:
        del parent, child_session_id
        raise BindingError("no child in synthetic smoke")


def main() -> int:
    if os.environ.get("TOKEN_IO_RUN_REAL_DECISIONS") != "1":
        print("status=not_run choice=none usage=none")
        return 0

    with tempfile.TemporaryDirectory(prefix="token-io-decisions-smoke-") as temp_dir:
        service = StateService(
            SyntheticProvider(),
            state_root=Path(temp_dir) / "state",
            rule_loader=RuleLoader(repository_root=Path(__file__).resolve().parents[2]),
        )
        service.workflow_open(
            WorkflowOpenRequest(
                mode_count=ModeCount(mode=CodingMode.SINGLE_AGENT, child_count=0),
                mode_source="explicit",
                source=SemanticRef(
                    uri="memory://synthetic-decisions-smoke",
                    content_hash="a" * 64,
                ),
                idempotency_key="synthetic-decisions-smoke-open",
            )
        )
        advisor = DecisionsAdvisor(
            service,
            RuleLoader(repository_root=Path(__file__).resolve().parents[2]),
            DecisionsRuntimeConfig(enabled=True, outbound_data_permitted=True),
        )
        advice = advisor.advise(
            TaskIntentInput(
                node_id=CheckpointNode.TASK_INTENT,
                requested_outcome="Add a unit test for a Python function.",
                deliverables=["one unit test"],
                task_signal="coding",
            )
        )
        choice = advice.suggested_choice or "none"
        usage = str(advice.total_tokens) if advice.total_tokens is not None else "none"
        failure_class = advice.failure_class or "none"
        http_status = str(advice.http_status) if advice.http_status is not None else "none"
        provider_code = advice.provider_error_code or "none"
        print(
            f"status={advice.status} reason={advice.reason} failure_class={failure_class} "
            f"http_status={http_status} provider_code={provider_code} "
            f"choice={choice} usage={usage}"
        )
        return 0 if advice.status == "available" and choice == "coding" else 1


if __name__ == "__main__":
    sys.exit(main())
