from __future__ import annotations

import pytest
from token_io_decoupling_workflow.task_plan_core import TaskPlanService

from token_io_decoupling.task_plan_factory import (
    TaskPlanFactoryError,
    load_task_plan_service,
)


def make_service() -> TaskPlanService:
    return TaskPlanService()


def make_invalid_service() -> object:
    return object()


def test_absent_factory_does_not_configure_a_backend() -> None:
    assert load_task_plan_service(None) is None


def test_factory_is_loaded_only_for_explicit_module_callable() -> None:
    service = load_task_plan_service(f"{__name__}:make_service")
    assert isinstance(service, TaskPlanService)
    assert service.capability()["status"] == "unavailable"


@pytest.mark.parametrize(
    ("spec", "reason"),
    [
        ("invalid", "factory_spec_invalid"),
        (f"{__name__}:missing_callable", "factory_import_failed"),
        (f"{__name__}:make_invalid_service", "factory_result_invalid"),
    ],
)
def test_invalid_factory_fails_closed(spec: str, reason: str) -> None:
    with pytest.raises(TaskPlanFactoryError) as exc:
        load_task_plan_service(spec)
    assert exc.value.reason == reason
