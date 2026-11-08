"""兼容原有导入路径；实现分别归属 compiled_rules 包中的职责模块。"""

from importlib import resources as resources

from .compiled_rules.context import (
    _budget_gaps as _budget_gaps,
)
from .compiled_rules.context import (
    _compiled_fragment as _compiled_fragment,
)
from .compiled_rules.context import (
    _context_bundle as _context_bundle,
)
from .compiled_rules.context import (
    _context_hash as _context_hash,
)
from .compiled_rules.contracts import (
    _DOCUMENT_FIELDS as _DOCUMENT_FIELDS,
)
from .compiled_rules.contracts import (
    _ENTRY_FIELDS as _ENTRY_FIELDS,
)
from .compiled_rules.contracts import (
    _REQUIRED_POLICY_SECTIONS as _REQUIRED_POLICY_SECTIONS,
)
from .compiled_rules.contracts import (
    _REQUIRED_RESOURCE_SECTIONS as _REQUIRED_RESOURCE_SECTIONS,
)
from .compiled_rules.contracts import (
    _SHA256 as _SHA256,
)
from .compiled_rules.contracts import (
    DEFAULT_CONTEXT_TEXT_BUDGET as DEFAULT_CONTEXT_TEXT_BUDGET,
)
from .compiled_rules.contracts import (
    MAX_COMPILED_RESOURCE_BYTES as MAX_COMPILED_RESOURCE_BYTES,
)
from .compiled_rules.contracts import (
    MAX_REMAINING_OWNER_REFS as MAX_REMAINING_OWNER_REFS,
)
from .compiled_rules.contracts import (
    SUPPORTED_CONTEXT_INDEX_VERSION as SUPPORTED_CONTEXT_INDEX_VERSION,
)
from .compiled_rules.contracts import (
    SUPPORTED_CONTRACT_VERSION as SUPPORTED_CONTRACT_VERSION,
)
from .compiled_rules.contracts import (
    CompiledDelegationPolicy as CompiledDelegationPolicy,
)
from .compiled_rules.contracts import (
    IncompatibleRuleContractError as IncompatibleRuleContractError,
)
from .compiled_rules.contracts import (
    RuleLoadError as RuleLoadError,
)
from .compiled_rules.contracts import (
    UnknownRuleNodeError as UnknownRuleNodeError,
)
from .compiled_rules.contracts import (
    UnsafeRulePathError as UnsafeRulePathError,
)
from .compiled_rules.contracts import (
    _canonical_hash as _canonical_hash,
)
from .compiled_rules.loader import (
    RuleLoader as RuleLoader,
)
from .compiled_rules.validation import (
    _validate_manifest as _validate_manifest,
)
from .compiled_rules.validation import (
    _validate_resource_sections as _validate_resource_sections,
)
