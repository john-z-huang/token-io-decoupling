"""兼容原有导入路径；实现分别归属 compilation 包中的职责模块。"""

from .compilation.cli import (
    main as main,
)
from .compilation.pipeline import (
    _LINK as _LINK,
)
from .compilation.pipeline import (
    COMPILER_VERSION as COMPILER_VERSION,
)
from .compilation.pipeline import (
    MAX_INSTRUCTION_CHARS as MAX_INSTRUCTION_CHARS,
)
from .compilation.pipeline import (
    SCHEMA_VERSION as SCHEMA_VERSION,
)
from .compilation.pipeline import (
    Compiler as Compiler,
)
from .compilation.pipeline import (
    compile_repository as compile_repository,
)

if __name__ == "__main__":
    raise SystemExit(main())
