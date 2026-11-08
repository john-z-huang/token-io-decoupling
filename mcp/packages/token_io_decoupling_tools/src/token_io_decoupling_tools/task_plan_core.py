"""兼容原有导入路径；实现分别归属 task_plans 包中的职责模块。"""

import importlib as importlib

from .task_plans.codec import (
    _canonical_json as _canonical_json,
)
from .task_plans.codec import (
    _event_line as _event_line,
)
from .task_plans.codec import (
    _history_identity as _history_identity,
)
from .task_plans.codec import (
    _json_object as _json_object,
)
from .task_plans.codec import (
    _request_hash as _request_hash,
)
from .task_plans.codec import (
    _unique_object as _unique_object,
)
from .task_plans.constants import (
    _EVENT_PREFIX as _EVENT_PREFIX,
)
from .task_plans.constants import (
    _EVENT_SUFFIX as _EVENT_SUFFIX,
)
from .task_plans.constants import (
    _EVENT_V2_PREFIX as _EVENT_V2_PREFIX,
)
from .task_plans.constants import (
    _GIT_IDENTITY_DOMAIN as _GIT_IDENTITY_DOMAIN,
)
from .task_plans.constants import (
    _GIT_IDENTITY_MAX_OUTPUT_BYTES as _GIT_IDENTITY_MAX_OUTPUT_BYTES,
)
from .task_plans.constants import (
    _GIT_IDENTITY_TIMEOUT_SECONDS as _GIT_IDENTITY_TIMEOUT_SECONDS,
)
from .task_plans.constants import (
    _GIT_REDIRECT_ENVIRONMENT as _GIT_REDIRECT_ENVIRONMENT,
)
from .task_plans.constants import (
    _GLOBAL_MEMORY_PREFIX as _GLOBAL_MEMORY_PREFIX,
)
from .task_plans.constants import (
    _HEADER_PREFIX as _HEADER_PREFIX,
)
from .task_plans.constants import (
    _HEADER_SUFFIX as _HEADER_SUFFIX,
)
from .task_plans.constants import (
    _HEADER_V2_PREFIX as _HEADER_V2_PREFIX,
)
from .task_plans.constants import (
    _KINDS as _KINDS,
)
from .task_plans.constants import (
    _OUTCOMES as _OUTCOMES,
)
from .task_plans.constants import (
    _PLAN_ID as _PLAN_ID,
)
from .task_plans.constants import (
    _RECORD_ID as _RECORD_ID,
)
from .task_plans.constants import (
    _REPOSITORY_ID as _REPOSITORY_ID,
)
from .task_plans.constants import (
    _REQUEST_ID as _REQUEST_ID,
)
from .task_plans.constants import (
    _REVISION as _REVISION,
)
from .task_plans.constants import (
    MAX_EVENTS as MAX_EVENTS,
)
from .task_plans.constants import (
    MAX_PLAN_BYTES as MAX_PLAN_BYTES,
)
from .task_plans.constants import (
    MAX_RECORDS_PER_OPERATION as MAX_RECORDS_PER_OPERATION,
)
from .task_plans.contracts import (
    _archive_request_project as _archive_request_project,
)
from .task_plans.contracts import (
    _check_expected as _check_expected,
)
from .task_plans.contracts import (
    _check_project_scope as _check_project_scope,
)
from .task_plans.contracts import (
    _current_state as _current_state,
)
from .task_plans.contracts import (
    _locate_replay as _locate_replay,
)
from .task_plans.contracts import (
    _observed_state as _observed_state,
)
from .task_plans.contracts import (
    _prepare_completion_records as _prepare_completion_records,
)
from .task_plans.contracts import (
    _receipt as _receipt,
)
from .task_plans.contracts import (
    _request_data as _request_data,
)
from .task_plans.contracts import (
    _verify_archive_snapshot as _verify_archive_snapshot,
)
from .task_plans.history import (
    _apply_history_event as _apply_history_event,
)
from .task_plans.history import (
    _history_legacy_prefix as _history_legacy_prefix,
)
from .task_plans.history import (
    _parse_history_header as _parse_history_header,
)
from .task_plans.history import (
    _parse_snapshot as _parse_snapshot,
)
from .task_plans.history import (
    _read_history_block as _read_history_block,
)
from .task_plans.history import (
    _replay_history as _replay_history,
)
from .task_plans.history import (
    _validate_history_event as _validate_history_event,
)
from .task_plans.history import (
    _validate_history_event_identity as _validate_history_event_identity,
)
from .task_plans.history import (
    _validate_history_header_identity as _validate_history_header_identity,
)
from .task_plans.identity import (
    _canonical_plan_project_root as _canonical_plan_project_root,
)
from .task_plans.identity import (
    _memory_root_for as _memory_root_for,
)
from .task_plans.identity import (
    _parse_git_identity as _parse_git_identity,
)
from .task_plans.identity import (
    _repository_id_for_checkout as _repository_id_for_checkout,
)
from .task_plans.identity import (
    _run_git_identity as _run_git_identity,
)
from .task_plans.records import (
    _apply_record_relationships as _apply_record_relationships,
)
from .task_plans.records import (
    _apply_records as _apply_records,
)
from .task_plans.records import (
    _validate_evidence as _validate_evidence,
)
from .task_plans.records import (
    _validate_evidence_entry as _validate_evidence_entry,
)
from .task_plans.records import (
    _validate_id as _validate_id,
)
from .task_plans.records import (
    _validate_plan_id as _validate_plan_id,
)
from .task_plans.records import (
    _validate_record as _validate_record,
)
from .task_plans.records import (
    _validate_record_relationships as _validate_record_relationships,
)
from .task_plans.records import (
    _validate_revision as _validate_revision,
)
from .task_plans.records import (
    _validate_text as _validate_text,
)
from .task_plans.service import (
    TaskPlanService as TaskPlanService,
)
from .task_plans.store import (
    SerenaMemoryStore as SerenaMemoryStore,
)
from .task_plans.store_io import (
    _discard_plan_temporary as _discard_plan_temporary,
)
from .task_plans.store_io import (
    _failed_plan_write_status as _failed_plan_write_status,
)
from .task_plans.types import (
    PlanStore as PlanStore,
)
from .task_plans.types import (
    TaskPlanFailure as TaskPlanFailure,
)
from .task_plans.types import (
    _HistoryHeader as _HistoryHeader,
)
from .task_plans.types import (
    _sha as _sha,
)
from .task_plans.types import (
    _Snapshot as _Snapshot,
)
from .task_plans.writer import (
    _append_event as _append_event,
)
