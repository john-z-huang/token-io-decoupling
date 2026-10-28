from __future__ import annotations

from pathlib import Path
from typing import Literal

import pytest
from token_io_decoupling_core.binding import BindingError, DenyingBindingProvider
from token_io_decoupling_core.models import (
    CodingMode,
    ModeCount,
    SemanticRef,
)
from token_io_decoupling_core.rules import RuleLoader
from token_io_decoupling_core.state_models import (
    CheckpointFact,
    EpochDimension,
    FactKey,
    WorkflowOpenRequest,
)
from token_io_decoupling_state.service import (
    StateService,
    _epochs_cover_changed_dimensions,
)


def ref(name: str) -> SemanticRef:
    return SemanticRef(uri=f"test://{name}", content_hash="a" * 64)


def source_rule_loader() -> RuleLoader:
    return RuleLoader(repository_root=Path(__file__).parents[3])


def request(
    *,
    children: int = 1,
    mode: CodingMode = CodingMode.MULTI_AGENT,
    mode_source: Literal["explicit", "default"] = "explicit",
    key: str = "open",
) -> WorkflowOpenRequest:
    return WorkflowOpenRequest(
        mode_count=ModeCount(mode=mode, child_count=children),
        mode_source=mode_source,
        source=ref("plan"),
        semantic_references=[],
        idempotency_key=key,
    )


def test_default_provider_denies_without_creating_state(tmp_path: Path) -> None:
    service = StateService(
        DenyingBindingProvider(),
        state_root=tmp_path / "state",
        rule_loader=source_rule_loader(),
    )
    with pytest.raises(BindingError):
        service.workflow_open(request())
    assert not (tmp_path / "state").exists()


def test_evidence_staleness_tracks_only_covered_epoch_dimensions() -> None:
    saved = (2, 3, 4)
    current = {
        "implementation_content": 2,
        "documentation": 4,
        "git_metadata": 5,
    }
    assert not _epochs_cover_changed_dimensions(
        [EpochDimension.IMPLEMENTATION_CONTENT.value], saved, current
    )
    assert _epochs_cover_changed_dimensions([EpochDimension.DOCUMENTATION.value], saved, current)
    assert _epochs_cover_changed_dimensions(
        [
            EpochDimension.IMPLEMENTATION_CONTENT.value,
            EpochDimension.DOCUMENTATION.value,
        ],
        saved,
        current,
    )
    content_change = {
        "implementation_content": 3,
        "documentation": 3,
        "git_metadata": 4,
    }
    assert _epochs_cover_changed_dimensions(
        [
            EpochDimension.IMPLEMENTATION_CONTENT.value,
            EpochDimension.DOCUMENTATION.value,
        ],
        saved,
        content_change,
    )
    assert _epochs_cover_changed_dimensions([EpochDimension.GIT_METADATA.value], saved, current)


def test_required_mode_and_objective_facts_cannot_be_marked_not_applicable() -> None:
    from pydantic import ValidationError
    from token_io_decoupling_core.state_models import FactNotApplicable

    for key in (FactKey.VALID_MODE_DECISION, FactKey.TASK_OBJECTIVE):
        with pytest.raises(ValidationError):
            CheckpointFact(
                fact_key=key,
                judgment=FactNotApplicable(
                    status="not_applicable", reason=ref("not-applicable-reason")
                ),
            )
