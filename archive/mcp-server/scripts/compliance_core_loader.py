"""Load the single standard-library compliance core for source and Skill snapshots."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

_MODULE_NAME = "_token_io_decoupling_compliance_core"
_CANONICAL_RELATIVE = Path(
    "mcp/packages/token_io_decoupling_core/src/token_io_decoupling_core/compliance_core.py"
)


def load_compliance_core() -> ModuleType:
    """Prefer the generated offline helper, then use the fixed authored source path."""
    script_dir = Path(__file__).resolve().parent
    candidates = (script_dir / "_compliance_core.py", script_dir.parent / _CANONICAL_RELATIVE)
    for candidate in candidates:
        if not candidate.is_file() or candidate.is_symlink():
            continue
        existing = sys.modules.get(_MODULE_NAME)
        if existing is not None:
            return existing
        spec = importlib.util.spec_from_file_location(_MODULE_NAME, candidate)
        if spec is None or spec.loader is None:
            continue
        module = importlib.util.module_from_spec(spec)
        sys.modules[_MODULE_NAME] = module
        try:
            spec.loader.exec_module(module)
        except Exception:
            sys.modules.pop(_MODULE_NAME, None)
            raise
        return module
    raise RuntimeError("shared compliance core source is unavailable")
