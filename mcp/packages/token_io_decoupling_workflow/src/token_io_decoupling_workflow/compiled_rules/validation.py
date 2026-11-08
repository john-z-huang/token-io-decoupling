"""校验批准资源的 manifest、结构和内容 Hash。"""

from __future__ import annotations

import hashlib

from token_io_decoupling_core.models import (
    RuleContextIndex,
    RuleRegistry,
)
from token_io_decoupling_core.registry_contract import (
    validate_supported_registry_shape,
)

from .contracts import (
    _ENTRY_FIELDS,
    _REQUIRED_RESOURCE_SECTIONS,
    _SHA256,
    IncompatibleRuleContractError,
    RuleLoadError,
)


def _validate_manifest(manifest: dict, document: dict, raw: bytes) -> None:
    """同时核对版本、中文标记、同批身份和原始字节 Hash，拒绝损坏资源。"""
    for value in (manifest, document):
        if type(value.get("schema_version")) is not int or value["schema_version"] != 3:
            raise IncompatibleRuleContractError("compiled instruction schema_version must be 3")
        if value.get("language") != "zh_cn":
            raise IncompatibleRuleContractError("compiled instructions must use zh_cn")
    build_id = document.get("build_id")
    if (
        not isinstance(build_id, str)
        or _SHA256.fullmatch(build_id) is None
        or manifest.get("build_id") != build_id
    ):
        raise IncompatibleRuleContractError("compiled instruction build identity mismatch")
    if manifest.get("files") != {"instructions.json": hashlib.sha256(raw).hexdigest()}:
        raise RuleLoadError("compiled instruction resource hash mismatch")


def _validate_resource_sections(document: dict) -> None:
    """固定需求与单项字段集合都须匹配，避免旧镜像形状绕过外层清单。"""
    for key in _REQUIRED_RESOURCE_SECTIONS:
        if not isinstance(document.get(key), dict):
            raise RuleLoadError(f"compiled instruction resource is missing {key}")
    validate_supported_registry_shape(document["registry"])
    RuleRegistry.model_validate(document["registry"])
    RuleContextIndex.model_validate(document["context_index"])
    for collection, fields in _ENTRY_FIELDS.items():
        for identity, entry in document[collection].items():
            if not isinstance(identity, str) or not isinstance(entry, dict) or set(entry) != fields:
                raise IncompatibleRuleContractError(
                    f"compiled {collection} entries must use one current instruction: {identity}"
                )
