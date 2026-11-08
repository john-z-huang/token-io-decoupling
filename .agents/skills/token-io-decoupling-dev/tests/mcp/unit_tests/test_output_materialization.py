"""物化任务分配模型的纯本地契约校验。"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from token_io_decoupling_tools.output_materialization import (
    MaterializationAssignment,
)


def test_specialized_instruction_materialization_is_not_a_product_output() -> None:

    with pytest.raises(ValidationError):
        MaterializationAssignment.model_validate({"output_class": "skill_instructions"})
