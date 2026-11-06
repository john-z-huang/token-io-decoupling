"""Load private repository documentation checks without a production dependency."""
from __future__ import annotations
import importlib.util
import sys
from pathlib import Path
from types import ModuleType
_MODULE_NAME = "_token_io_decoupling_compliance_core"
def load_compliance_core() -> ModuleType:
    if _MODULE_NAME in sys.modules:
        return sys.modules[_MODULE_NAME]
    path = Path(__file__).resolve().with_name("_compliance_core.py")
    spec = importlib.util.spec_from_file_location(_MODULE_NAME, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("private compliance implementation unavailable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[_MODULE_NAME] = module
    spec.loader.exec_module(module)
    return module
