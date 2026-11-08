"""兼容原有导入路径；实现分别归属 _context_exchange 包中的职责模块。"""

from _context_exchange.capsule import (
    validate_capsule as validate_capsule,
)
from _context_exchange.cli import (
    main as main,
)
from _context_exchange.coordination import (
    _probe_ignore_preservation as _probe_ignore_preservation,
)
from _context_exchange.coordination import (
    _validate_capsule_hierarchy as _validate_capsule_hierarchy,
)
from _context_exchange.coordination import (
    check_ignore_policy as check_ignore_policy,
)
from _context_exchange.coordination import (
    validate_hierarchy as validate_hierarchy,
)
from _context_exchange.filesystem import (
    git_output as git_output,
)
from _context_exchange.filesystem import (
    is_symlink as is_symlink,
)
from _context_exchange.filesystem import (
    lstat_existing as lstat_existing,
)
from _context_exchange.filesystem import (
    run_git as run_git,
)
from _context_exchange.filesystem import (
    safe_source_path as safe_source_path,
)
from _context_exchange.manifest import (
    _capsule_directory as _capsule_directory,
)
from _context_exchange.manifest import (
    _capsule_required_files as _capsule_required_files,
)
from _context_exchange.manifest import (
    _capsule_source_entries as _capsule_source_entries,
)
from _context_exchange.manifest import (
    _read_capsule_manifest as _read_capsule_manifest,
)
from _context_exchange.manifest import (
    _validate_capsule_manifest as _validate_capsule_manifest,
)
from _context_exchange.models import (
    CAPSULE_DIR as CAPSULE_DIR,
)
from _context_exchange.models import (
    EXCHANGE_DIR as EXCHANGE_DIR,
)
from _context_exchange.models import (
    IGNORE_RULE as IGNORE_RULE,
)
from _context_exchange.models import (
    MAX_CONTEXT_BYTES as MAX_CONTEXT_BYTES,
)
from _context_exchange.models import (
    SOURCE_ROW_RE as SOURCE_ROW_RE,
)
from _context_exchange.models import (
    SourceEntry as SourceEntry,
)
from _context_exchange.models import (
    _CapsuleWorktreeSnapshot as _CapsuleWorktreeSnapshot,
)
from _context_exchange.snapshot import (
    _capsule_snapshot_mismatches as _capsule_snapshot_mismatches,
)
from _context_exchange.snapshot import (
    _check_capsule_sources as _check_capsule_sources,
)
from _context_exchange.snapshot import (
    _read_capsule_snapshot as _read_capsule_snapshot,
)

if __name__ == "__main__":
    raise SystemExit(main())
