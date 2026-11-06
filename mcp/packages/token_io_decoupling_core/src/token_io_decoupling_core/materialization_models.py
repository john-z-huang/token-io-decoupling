"""Finite request and authority contracts for bounded Worker output materialization."""

from __future__ import annotations

from typing import Annotated, Literal, TypeAlias

from pydantic import Field, StrictBool, StrictInt, StrictStr, field_validator, model_validator

from token_io_decoupling_core.models import StrictModel

MAX_MATERIALIZATION_FILES = 16
MAX_MATERIALIZATION_PATH_CHARS = 512
MAX_MATERIALIZATION_TEXT_CHARS = 131_072
MAX_MATERIALIZATION_BATCH_UTF8_BYTES = 524_288
MAX_FACT_HEADINGS = 8
MAX_FACT_ITEMS = 64
MAX_INSPECT_CHARS = 8_192
DEFAULT_INSPECT_CHARS = 2_048

Sha256Hex = Annotated[
    StrictStr,
    Field(min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$"),
]
OpaquePreparedId = Annotated[
    StrictStr,
    Field(min_length=32, max_length=32, pattern=r"^[0-9a-f]{32}$"),
]
BoundedId = Annotated[
    StrictStr,
    Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_.-]+$"),
]
BoundedTitle = Annotated[StrictStr, Field(min_length=1, max_length=256)]
BoundedFactText = Annotated[StrictStr, Field(max_length=8_192)]
MaterializationOperation: TypeAlias = Literal["create", "replace"]
MaterializationTemplateName: TypeAlias = Literal["literal_text", "json_document", "fact_markdown"]
MaterializationPolicyScope: TypeAlias = Literal["generic_project"]
MaterializationRole: TypeAlias = Literal["Primary Output"]
MaterializationOutputClass: TypeAlias = Literal["code_configuration"]


class DirectoryIdentity(StrictModel):
    """Identity of an already-opened operator-configured directory descriptor."""

    device: Annotated[StrictInt, Field(ge=0)]
    inode: Annotated[StrictInt, Field(ge=0)]


class AbsentBaseline(StrictModel):
    state: Literal["absent"]


class Sha256Baseline(StrictModel):
    state: Literal["sha256"]
    value: Sha256Hex


MaterializationBaseline: TypeAlias = Annotated[
    AbsentBaseline | Sha256Baseline,
    Field(discriminator="state"),
]


class LiteralTextTemplate(StrictModel):
    kind: Literal["literal_text"]
    text: Annotated[StrictStr, Field(max_length=MAX_MATERIALIZATION_TEXT_CHARS)]


class JsonDocumentTemplate(StrictModel):
    """JSON is supplied as bounded text and validated locally; the wire schema is finite."""

    kind: Literal["json_document"]
    json_text: Annotated[StrictStr, Field(max_length=MAX_MATERIALIZATION_TEXT_CHARS)]


class FactHeading(StrictModel):
    id: BoundedId
    title: BoundedTitle


class SourceFact(StrictModel):
    id: BoundedId
    heading_id: BoundedId
    text: BoundedFactText


class FactMarkdownTemplate(StrictModel):
    kind: Literal["fact_markdown"]
    headings: Annotated[list[FactHeading], Field(min_length=1, max_length=MAX_FACT_HEADINGS)]
    facts: Annotated[list[SourceFact], Field(min_length=1, max_length=MAX_FACT_ITEMS)]
    ordering: Literal["source", "responses"] = "source"

    @model_validator(mode="after")
    def validate_ids_and_references(self) -> FactMarkdownTemplate:
        heading_ids = [heading.id for heading in self.headings]
        if len(set(heading_ids)) != len(heading_ids):
            raise ValueError("fact_markdown_heading_ids_must_be_unique")
        fact_ids = [fact.id for fact in self.facts]
        if len(set(fact_ids)) != len(fact_ids):
            raise ValueError("fact_markdown_fact_ids_must_be_unique")
        known_headings = set(heading_ids)
        if any(fact.heading_id not in known_headings for fact in self.facts):
            raise ValueError("fact_markdown_fact_heading_unknown")
        return self


MaterializationTemplate: TypeAlias = Annotated[
    LiteralTextTemplate | JsonDocumentTemplate | FactMarkdownTemplate,
    Field(discriminator="kind"),
]


def _validate_exact_relative_leaf_path(value: str) -> str:
    if value.startswith("/") or "\\" in value or any(ord(char) < 32 for char in value):
        raise ValueError("materialization_path_must_be_a_relative_posix_leaf_path")
    parts = value.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise ValueError("materialization_path_must_be_normalized")
    if any(part.lower() in {".git", ".hg", ".svn"} for part in parts):
        raise ValueError("materialization_path_cannot_target_repository_control_data")
    if any(char in value for char in "*?[]"):
        raise ValueError("materialization_path_cannot_contain_globs")
    return value


class MaterializationFileSpec(StrictModel):
    path: Annotated[StrictStr, Field(min_length=1, max_length=MAX_MATERIALIZATION_PATH_CHARS)]
    operation: MaterializationOperation
    baseline: MaterializationBaseline
    template: MaterializationTemplate

    @field_validator("path")
    @classmethod
    def validate_exact_relative_leaf(cls, value: str) -> str:
        return _validate_exact_relative_leaf_path(value)

    @model_validator(mode="after")
    def validate_operation_baseline(self) -> MaterializationFileSpec:
        if self.operation == "create" and not isinstance(self.baseline, AbsentBaseline):
            raise ValueError("materialization_create_requires_absent_baseline")
        if self.operation == "replace" and not isinstance(self.baseline, Sha256Baseline):
            raise ValueError("materialization_replace_requires_sha256_baseline")
        return self


class MaterializationPrepareRequest(StrictModel):
    action: Literal["prepare"]
    files: Annotated[
        list[MaterializationFileSpec],
        Field(min_length=1, max_length=MAX_MATERIALIZATION_FILES),
    ]
    outbound_data_permitted: StrictBool = False

    @model_validator(mode="after")
    def validate_paths_unique(self) -> MaterializationPrepareRequest:
        paths = [file.path for file in self.files]
        if len(set(paths)) != len(paths):
            raise ValueError("materialization_candidate_paths_must_be_unique")
        return self


class MaterializationInspectRequest(StrictModel):
    action: Literal["inspect"]
    prepared_id: OpaquePreparedId
    expected_manifest_hash: Sha256Hex
    file_index: Annotated[StrictInt, Field(ge=0, lt=MAX_MATERIALIZATION_FILES)]
    offset: Annotated[StrictInt, Field(ge=0, le=MAX_MATERIALIZATION_TEXT_CHARS)] = 0
    max_chars: Annotated[StrictInt, Field(ge=1, le=MAX_INSPECT_CHARS)] = DEFAULT_INSPECT_CHARS


class MaterializationApplyRequest(StrictModel):
    action: Literal["apply"]
    prepared_id: OpaquePreparedId
    expected_manifest_hash: Sha256Hex


MaterializationRequest: TypeAlias = Annotated[
    MaterializationPrepareRequest | MaterializationInspectRequest | MaterializationApplyRequest,
    Field(discriminator="action"),
]


class MaterializeDecoupledOutputPayload(StrictModel):
    request: MaterializationRequest


class OutputMaterializationGrant(StrictModel):
    """Independent operator grant; this record never comes from a tool payload."""

    grant_id: Annotated[StrictStr, Field(min_length=1, max_length=128)]
    revision: Annotated[StrictInt, Field(ge=1)]
    active: StrictBool
    policy_version: Literal[2]
    project_id: Annotated[StrictStr, Field(min_length=1, max_length=128)]
    root_session_id: Annotated[StrictStr, Field(min_length=1, max_length=128)]
    worker_session_id: Annotated[StrictStr, Field(min_length=1, max_length=128)]
    allocation_id: Annotated[StrictStr, Field(min_length=1, max_length=128)]
    role: MaterializationRole
    output_class: MaterializationOutputClass
    slice_id: Annotated[StrictStr, Field(min_length=1, max_length=128)]
    assignment_hash: Sha256Hex
    project_root: DirectoryIdentity
    artifact_root: DirectoryIdentity
    policy_scope: MaterializationPolicyScope
    allowed_paths: Annotated[
        list[Annotated[StrictStr, Field(min_length=1, max_length=MAX_MATERIALIZATION_PATH_CHARS)]],
        Field(min_length=1, max_length=MAX_MATERIALIZATION_FILES),
    ]
    allowed_operations: Annotated[list[MaterializationOperation], Field(min_length=1, max_length=2)]
    allowed_templates: Annotated[
        list[MaterializationTemplateName], Field(min_length=1, max_length=3)
    ]
    allow_responses_ordering: StrictBool = False

    @model_validator(mode="before")
    @classmethod
    def require_exact_policy_version_type(cls, value: object) -> object:
        if isinstance(value, dict) and "policy_version" in value:
            version = value["policy_version"]
            if type(version) is not int or version != 2:
                raise ValueError("materialization_policy_version_invalid")
        return value

    @model_validator(mode="after")
    def validate_grant_scope(self) -> OutputMaterializationGrant:
        if not self.active:
            raise ValueError("materialization_grant_revoked")
        if self.output_class not in {"code_configuration"}:
            raise ValueError("materialization_role_output_class_mismatch")
        for path in self.allowed_paths:
            _validate_exact_relative_leaf_path(path)
        if len(set(self.allowed_paths)) != len(self.allowed_paths):
            raise ValueError("materialization_grant_paths_must_be_unique")
        if len(set(self.allowed_operations)) != len(self.allowed_operations):
            raise ValueError("materialization_grant_operations_must_be_unique")
        if len(set(self.allowed_templates)) != len(self.allowed_templates):
            raise ValueError("materialization_grant_templates_must_be_unique")
        return self


class MaterializationBindingFingerprint(StrictModel):
    project_id: Annotated[StrictStr, Field(min_length=1, max_length=128)]
    root_session_id: Annotated[StrictStr, Field(min_length=1, max_length=128)]
    worker_session_id: Annotated[StrictStr, Field(min_length=1, max_length=128)]
    allocation_id: Annotated[StrictStr, Field(min_length=1, max_length=128)]
    role: MaterializationRole
    output_class: MaterializationOutputClass
    slice_id: Annotated[StrictStr, Field(min_length=1, max_length=128)]
    assignment_hash: Sha256Hex


class PreparedMaterializationFile(StrictModel):
    path: Annotated[StrictStr, Field(min_length=1, max_length=MAX_MATERIALIZATION_PATH_CHARS)]
    operation: MaterializationOperation
    baseline: MaterializationBaseline
    template: MaterializationTemplateName
    content_sha256: Sha256Hex
    content_bytes: Annotated[StrictInt, Field(ge=0, le=MAX_MATERIALIZATION_BATCH_UTF8_BYTES)]
    content_chars: Annotated[StrictInt, Field(ge=0, le=MAX_MATERIALIZATION_TEXT_CHARS)]
    artifact_name: Annotated[StrictStr, Field(pattern=r"^candidate-[0-9]{2}\.bin$")]


class PreparedMaterializationManifest(StrictModel):
    version: Literal[1]
    prepared_id: OpaquePreparedId
    policy_version: Literal[2]
    binding: MaterializationBindingFingerprint
    grant_id: Annotated[StrictStr, Field(min_length=1, max_length=128)]
    grant_revision: Annotated[StrictInt, Field(ge=1)]
    grant_sha256: Sha256Hex
    project_root: DirectoryIdentity
    artifact_root: DirectoryIdentity
    policy_scope: MaterializationPolicyScope
    files: Annotated[
        list[PreparedMaterializationFile],
        Field(min_length=1, max_length=MAX_MATERIALIZATION_FILES),
    ]

    @model_validator(mode="before")
    @classmethod
    def require_exact_version_types(cls, value: object) -> object:
        if isinstance(value, dict):
            for field_name in ("version", "policy_version"):
                if field_name in value:
                    version = value[field_name]
                    if type(version) is not int or version != (1 if field_name == "version" else 2):
                        raise ValueError("materialization_manifest_version_invalid")
        return value


class FactOrderingItem(StrictModel):
    file_index: Annotated[StrictInt, Field(ge=0, lt=MAX_MATERIALIZATION_FILES)]
    fact_ids: Annotated[list[BoundedId], Field(min_length=1, max_length=MAX_FACT_ITEMS)]


class FactOrderingPlan(StrictModel):
    """Responses may reorder supplied IDs only; source text is rendered locally."""

    files: Annotated[
        list[FactOrderingItem], Field(min_length=1, max_length=MAX_MATERIALIZATION_FILES)
    ]


class MaterializationFileReceipt(StrictModel):
    file_index: Annotated[StrictInt, Field(ge=0, lt=MAX_MATERIALIZATION_FILES)]
    path: Annotated[StrictStr, Field(min_length=1, max_length=MAX_MATERIALIZATION_PATH_CHARS)]
    status: Literal["applied", "already_identical", "conflict", "not_attempted", "uncertain"]
    actual_sha256: Sha256Hex | None = None


class MaterializationReceipt(StrictModel):
    version: Literal[1]
    prepared_id: OpaquePreparedId
    manifest_sha256: Sha256Hex
    status: Literal["applied", "already_identical", "partial", "conflict", "uncertain"]
    files: Annotated[
        list[MaterializationFileReceipt],
        Field(min_length=1, max_length=MAX_MATERIALIZATION_FILES),
    ]
