"""兼容原有导入路径；实现分别归属 artifact_storage 包中的职责模块。"""

from .artifact_storage.filesystem import (
    MaterializationStorageError as MaterializationStorageError,
)
from .artifact_storage.service import (
    MaterializationStorage as MaterializationStorage,
)
