from __future__ import annotations

from importlib import import_module
from typing import Any

from token_io_decoupling_workflow.task_plan_core import TaskPlanService


class TaskPlanFactoryError(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def load_task_plan_service(factory_spec: str | None) -> TaskPlanService | None:
    """Load trusted operator code only when the explicit startup option is present."""
    if factory_spec is None:
        return None
    module_name, separator, attribute_name = factory_spec.partition(":")
    if not separator or not module_name or not attribute_name or attribute_name.startswith("_"):
        raise TaskPlanFactoryError("factory_spec_invalid")
    try:
        module = import_module(module_name)
        factory: Any = getattr(module, attribute_name)
    except Exception as exc:
        raise TaskPlanFactoryError("factory_import_failed") from exc
    if not callable(factory):
        raise TaskPlanFactoryError("factory_not_callable")
    try:
        service = factory()
    except Exception as exc:
        raise TaskPlanFactoryError("factory_call_failed") from exc
    if not isinstance(service, TaskPlanService):
        raise TaskPlanFactoryError("factory_result_invalid")
    return service
