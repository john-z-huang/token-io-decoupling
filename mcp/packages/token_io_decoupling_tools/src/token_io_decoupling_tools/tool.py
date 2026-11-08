"""兼容原有导入路径；实现分别归属 registration 包中的职责模块。"""

from .registration.annotations import (
    _AI_READ as _AI_READ,
)
from .registration.annotations import (
    _LOCAL_DESTRUCTIVE as _LOCAL_DESTRUCTIVE,
)
from .registration.annotations import (
    _LOCAL_IDEMPOTENT as _LOCAL_IDEMPOTENT,
)
from .registration.annotations import (
    _LOCAL_READ as _LOCAL_READ,
)
from .registration.annotations import (
    _LOCAL_WRITE as _LOCAL_WRITE,
)
from .registration.annotations import (
    _MEMORY_READ as _MEMORY_READ,
)
from .registration.annotations import (
    _REMOTE_DESTRUCTIVE as _REMOTE_DESTRUCTIVE,
)
from .registration.annotations import (
    _REMOTE_IDEMPOTENT as _REMOTE_IDEMPOTENT,
)
from .registration.annotations import (
    _REMOTE_READ as _REMOTE_READ,
)
from .registration.annotations import (
    _REMOTE_WRITE as _REMOTE_WRITE,
)
from .registration.local import (
    ChangedContent as ChangedContent,
)
from .registration.local import (
    MemoryPath as MemoryPath,
)
from .registration.local import (
    TailLines as TailLines,
)
from .registration.local import (
    register_tools as register_tools,
)
from .registration.upstream import (
    _UPSTREAM_TOOLS as _UPSTREAM_TOOLS,
)
