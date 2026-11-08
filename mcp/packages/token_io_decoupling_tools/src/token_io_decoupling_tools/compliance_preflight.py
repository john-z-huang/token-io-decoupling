"""兼容原有导入路径；实现分别归属 compliance 包中的职责模块。"""

from .compliance.reading import (
    _ReadResult as _ReadResult,
)
from .compliance.reading import (
    _same_file_state as _same_file_state,
)
from .compliance.service import (
    CompliancePreflightService as CompliancePreflightService,
)
from .compliance.service import (
    _check as _check,
)
from .compliance.service import (
    _unavailable_result as _unavailable_result,
)
from .compliance.service import (
    validate_decoupling_compliance as validate_decoupling_compliance,
)
