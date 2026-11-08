"""兼容原有导入路径；实现分别归属 materialization 包中的职责模块。"""

from .materialization.models import (
    _CALLER_BINDING as _CALLER_BINDING,
)
from .materialization.models import (
    _REQUEST_ADAPTER as _REQUEST_ADAPTER,
)
from .materialization.models import (
    MaterializationAssignment as MaterializationAssignment,
)
from .materialization.models import (
    MaterializationAuthorizationContext as MaterializationAuthorizationContext,
)
from .materialization.models import (
    MaterializationAuthorizationProvider as MaterializationAuthorizationProvider,
)
from .materialization.models import (
    MaterializationGrantProvider as MaterializationGrantProvider,
)
from .materialization.models import (
    MaterializationReceiptStatus as MaterializationReceiptStatus,
)
from .materialization.models import (
    OutputMaterializerConfig as OutputMaterializerConfig,
)
from .materialization.models import (
    _MaterializationFailure as _MaterializationFailure,
)
from .materialization.models import (
    materialization_assignment_hash as materialization_assignment_hash,
)
from .materialization.service import (
    OutputMaterializationService as OutputMaterializationService,
)
