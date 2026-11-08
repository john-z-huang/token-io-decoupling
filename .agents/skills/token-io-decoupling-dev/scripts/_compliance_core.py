"""兼容原有导入路径；实现分别归属 _author_checks 包中的职责模块。"""

from _author_checks.candidates import (
    _candidate_link_checks as _candidate_link_checks,
)
from _author_checks.candidates import (
    _candidate_link_rule_checks as _candidate_link_rule_checks,
)
from _author_checks.candidates import (
    _candidate_scope_checks as _candidate_scope_checks,
)
from _author_checks.candidates import (
    _candidate_structure_checks as _candidate_structure_checks,
)
from _author_checks.candidates import (
    _generic_candidate_findings as _generic_candidate_findings,
)
from _author_checks.candidates import (
    evaluate_candidate_checks as evaluate_candidate_checks,
)
from _author_checks.constants import (
    _FENCE_RE as _FENCE_RE,
)
from _author_checks.constants import (
    _HEADING_RE as _HEADING_RE,
)
from _author_checks.constants import (
    _INLINE_CODE_RE as _INLINE_CODE_RE,
)
from _author_checks.constants import (
    _LANGUAGE_SWITCH_LABELS as _LANGUAGE_SWITCH_LABELS,
)
from _author_checks.constants import (
    _LINK_RE as _LINK_RE,
)
from _author_checks.constants import (
    _MODULES as _MODULES,
)
from _author_checks.constants import (
    _MULTILINGUAL_FENCE_RE as _MULTILINGUAL_FENCE_RE,
)
from _author_checks.constants import (
    _PAIR_ROOT_SET as _PAIR_ROOT_SET,
)
from _author_checks.constants import (
    _PAIR_ROOT_ZH_NAMES as _PAIR_ROOT_ZH_NAMES,
)
from _author_checks.constants import (
    _ROUTE_MODULES as _ROUTE_MODULES,
)
from _author_checks.constants import (
    LAYER01_HEADINGS as LAYER01_HEADINGS,
)
from _author_checks.constants import (
    LAYER01_NAVIGATION as LAYER01_NAVIGATION,
)
from _author_checks.constants import (
    MAX_BATCH_UTF8_BYTES as MAX_BATCH_UTF8_BYTES,
)
from _author_checks.constants import (
    MAX_CANDIDATES as MAX_CANDIDATES,
)
from _author_checks.constants import (
    MAX_CHECK_MESSAGE_CHARS as MAX_CHECK_MESSAGE_CHARS,
)
from _author_checks.constants import (
    MAX_DIRECT_TARGETS as MAX_DIRECT_TARGETS,
)
from _author_checks.constants import (
    MAX_FILE_CHARS as MAX_FILE_CHARS,
)
from _author_checks.constants import (
    MAX_OUTPUT_CHECKS as MAX_OUTPUT_CHECKS,
)
from _author_checks.constants import (
    MAX_PATH_CHARS as MAX_PATH_CHARS,
)
from _author_checks.constants import (
    OPERATIONS as OPERATIONS,
)
from _author_checks.constants import (
    PAIR_ROOTS as PAIR_ROOTS,
)
from _author_checks.constants import (
    POLICY_SCOPES as POLICY_SCOPES,
)
from _author_checks.constants import (
    POLICY_VERSION as POLICY_VERSION,
)
from _author_checks.constants import (
    STATUS_VALUES as STATUS_VALUES,
)
from _author_checks.constants import (
    ZH_SUFFIX as ZH_SUFFIX,
)
from _author_checks.findings import (
    _finding as _finding,
)
from _author_checks.findings import (
    build_result as build_result,
)
from _author_checks.language import (
    candidate_mirror_finding as candidate_mirror_finding,
)
from _author_checks.language import (
    multilingual_cross_language_issues as multilingual_cross_language_issues,
)
from _author_checks.language import (
    multilingual_mirror_issues as multilingual_mirror_issues,
)
from _author_checks.links import (
    _advance_fence as _advance_fence,
)
from _author_checks.links import (
    _document_dependency_issues as _document_dependency_issues,
)
from _author_checks.links import (
    _resolve_document_link as _resolve_document_link,
)
from _author_checks.links import (
    _single_document_link_issues as _single_document_link_issues,
)
from _author_checks.links import (
    document_link_findings as document_link_findings,
)
from _author_checks.links import (
    document_link_issues as document_link_issues,
)
from _author_checks.links import (
    links_in_markdown as links_in_markdown,
)
from _author_checks.links import (
    normalize_markdown_target as normalize_markdown_target,
)
from _author_checks.links import (
    normalize_multilingual_target as normalize_multilingual_target,
)
from _author_checks.paths import (
    _allowed_route_link as _allowed_route_link,
)
from _author_checks.paths import (
    _coding_reference_layer as _coding_reference_layer,
)
from _author_checks.paths import (
    allowed_link as allowed_link,
)
from _author_checks.paths import (
    counterpart as counterpart,
)
from _author_checks.paths import (
    is_bilingual_document as is_bilingual_document,
)
from _author_checks.paths import (
    is_language_switch as is_language_switch,
)
from _author_checks.paths import (
    is_navigation_document as is_navigation_document,
)
from _author_checks.paths import (
    mirror_path as mirror_path,
)
from _author_checks.paths import (
    path_language as path_language,
)
from _author_checks.paths import (
    path_layer as path_layer,
)
from _author_checks.sections import (
    _check_layer01_section_content as _check_layer01_section_content,
)
from _author_checks.sections import (
    is_layer01_path as is_layer01_path,
)
from _author_checks.sections import (
    layer01_section_issues as layer01_section_issues,
)
from _author_checks.sections import (
    top_level_sections as top_level_sections,
)
from _author_checks.validation import (
    ComplianceInputError as ComplianceInputError,
)
from _author_checks.validation import (
    _candidate_content_bytes as _candidate_content_bytes,
)
from _author_checks.validation import (
    _validate_candidate_baseline as _validate_candidate_baseline,
)
from _author_checks.validation import (
    validate_candidate_list as validate_candidate_list,
)
from _author_checks.validation import (
    validate_relative_posix_path as validate_relative_posix_path,
)
