import copy
from typing import Any

MANIFEST_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Token I/O Runtime Instructions Manifest v1",
    "type": "object",
    "additionalProperties": False,
    "required": [
        "manifest_format",
        "policy_contract_version",
        "legacy_context_index_version",
        "legacy_source_hashes",
        "budgets",
        "source_units",
        "runtime_entries",
    ],
    "$defs": {
        "stable_id": {"type": "string", "pattern": "^[a-z][a-z0-9._-]{0,119}$"},
        "sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
        "source_selector": {
            "type": "object",
            "additionalProperties": False,
            "required": ["source_unit_id", "quote", "occurrence"],
            "properties": {
                "source_unit_id": {"$ref": "#/$defs/stable_id"},
                "quote": {"type": "string", "minLength": 1},
                "occurrence": {"type": "integer", "minimum": 0},
            },
        },
        "link_selector": {
            "type": "object",
            "additionalProperties": False,
            "required": ["raw", "occurrence"],
            "properties": {
                "raw": {"type": "string", "minLength": 1},
                "occurrence": {"type": "integer", "minimum": 0},
            },
        },
        "reference": {
            "oneOf": [
                {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "class",
                        "selector",
                        "label",
                        "destination",
                        "target_source_unit_id",
                    ],
                    "properties": {
                        "class": {"const": "required"},
                        "selector": {"$ref": "#/$defs/link_selector"},
                        "label": {"type": "string"},
                        "destination": {"type": "string"},
                        "target_source_unit_id": {"$ref": "#/$defs/stable_id"},
                    },
                },
                {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "class",
                        "selector",
                        "label",
                        "destination",
                        "target_source_unit_id",
                        "condition_id",
                        "trigger_selector",
                    ],
                    "properties": {
                        "class": {"const": "conditional"},
                        "selector": {"$ref": "#/$defs/link_selector"},
                        "label": {"type": "string"},
                        "destination": {"type": "string"},
                        "target_source_unit_id": {"$ref": "#/$defs/stable_id"},
                        "condition_id": {"$ref": "#/$defs/stable_id"},
                        "trigger_selector": {"$ref": "#/$defs/source_selector"},
                    },
                },
                {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["class", "selector", "label", "destination"],
                    "properties": {
                        "class": {"const": "navigation"},
                        "selector": {"$ref": "#/$defs/link_selector"},
                        "label": {"type": "string"},
                        "destination": {"type": "string"},
                        "target_source_unit_id": {"$ref": "#/$defs/stable_id"},
                    },
                },
                {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "class",
                        "selector",
                        "label",
                        "destination",
                        "target_source_unit_id",
                        "included_in_source_unit_id",
                    ],
                    "properties": {
                        "class": {"const": "internal_already_included"},
                        "selector": {"$ref": "#/$defs/link_selector"},
                        "label": {"type": "string"},
                        "destination": {"type": "string"},
                        "target_source_unit_id": {"$ref": "#/$defs/stable_id"},
                        "included_in_source_unit_id": {"$ref": "#/$defs/stable_id"},
                    },
                },
            ],
        },
        "semantic_dependency": {
            "type": "object",
            "additionalProperties": False,
            "required": ["class", "target_source_unit_id", "provenance"],
            "properties": {
                "class": {"enum": ["required", "conditional"]},
                "target_source_unit_id": {"$ref": "#/$defs/stable_id"},
                "condition_id": {"$ref": "#/$defs/stable_id"},
                "trigger_selector": {"$ref": "#/$defs/source_selector"},
                "provenance": {
                    "oneOf": [
                        {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["kind", "selector"],
                            "properties": {
                                "kind": {"const": "markdown_quote"},
                                "selector": {"$ref": "#/$defs/source_selector"},
                            },
                        },
                        {
                            "type": "object",
                            "additionalProperties": False,
                            "required": [
                                "kind",
                                "json_pointer",
                                "fragment_id",
                                "dependency_fragment_id",
                                "source_sha256",
                            ],
                            "properties": {
                                "kind": {"const": "legacy_index_dependency"},
                                "json_pointer": {
                                    "type": "string",
                                    "pattern": "^/fragments/[0-9]+/dependencies/[0-9]+$",
                                },
                                "fragment_id": {"$ref": "#/$defs/stable_id"},
                                "dependency_fragment_id": {"$ref": "#/$defs/stable_id"},
                                "source_sha256": {"$ref": "#/$defs/sha256"},
                            },
                        },
                    ],
                },
            },
            "allOf": [
                {
                    "if": {"properties": {"class": {"const": "conditional"}}},
                    "then": {
                        "required": ["condition_id", "trigger_selector"],
                        "properties": {
                            "provenance": {"properties": {"kind": {"const": "markdown_quote"}}}
                        },
                    },
                    "else": {
                        "not": {
                            "anyOf": [
                                {"required": ["condition_id"]},
                                {"required": ["trigger_selector"]},
                            ]
                        }
                    },
                },
            ],
        },
        "source_unit": {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "source_unit_id",
                "source_kind",
                "locale",
                "source",
                "expected_hashes",
                "references",
            ],
            "properties": {
                "source_unit_id": {"$ref": "#/$defs/stable_id"},
                "source_kind": {"enum": ["fragment", "owner", "semantic_owner", "node_mapping"]},
                "legacy_id": {"$ref": "#/$defs/stable_id"},
                "legacy_node_id": {"$ref": "#/$defs/stable_id"},
                "locale": {"enum": ["en", "zh_cn"]},
                "source": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["path", "heading"],
                    "properties": {
                        "path": {"type": "string", "minLength": 1},
                        "heading": {"type": "string", "minLength": 1},
                    },
                },
                "expected_hashes": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["source_sha256", "excerpt_sha256"],
                    "properties": {
                        "source_sha256": {"$ref": "#/$defs/sha256"},
                        "excerpt_sha256": {"$ref": "#/$defs/sha256"},
                    },
                },
                "references": {
                    "type": "array",
                    "items": {"$ref": "#/$defs/reference"},
                },
                "semantic_dependencies": {
                    "type": "array",
                    "items": {"$ref": "#/$defs/semantic_dependency"},
                },
            },
        },
        "owner_view": {
            "type": "object",
            "additionalProperties": False,
            "required": ["legacy_owner_id", "locale", "source_unit_ids"],
            "properties": {
                "legacy_owner_id": {"$ref": "#/$defs/stable_id"},
                "locale": {"enum": ["en", "zh_cn"]},
                "source_unit_ids": {
                    "type": "array",
                    "minItems": 1,
                    "uniqueItems": True,
                    "items": {"$ref": "#/$defs/stable_id"},
                },
            },
        },
        "runtime_entry": {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "tool_id",
                "node_id",
                "stage_id",
                "locale",
                "source_unit_ids",
                "actions",
                "branches",
            ],
            "properties": {
                "tool_id": {"$ref": "#/$defs/stable_id"},
                "node_id": {"$ref": "#/$defs/stable_id"},
                "stage_id": {"$ref": "#/$defs/stable_id"},
                "locale": {"enum": ["en", "zh_cn"]},
                "source_unit_ids": {
                    "type": "array",
                    "minItems": 1,
                    "uniqueItems": True,
                    "items": {"$ref": "#/$defs/stable_id"},
                },
                "actions": {
                    "type": "array",
                    "minItems": 1,
                    "items": {"$ref": "#/$defs/source_selector"},
                },
                "branches": {
                    "type": "array",
                    "minItems": 1,
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["id", "trigger", "actions", "pass", "failure"],
                        "properties": {
                            "id": {"$ref": "#/$defs/stable_id"},
                            "legacy_branch": {"type": "string", "minLength": 1},
                            "trigger": {"$ref": "#/$defs/source_selector"},
                            "actions": {"$ref": "#/$defs/source_selector"},
                            "pass": {"$ref": "#/$defs/source_selector"},
                            "failure": {"$ref": "#/$defs/source_selector"},
                        },
                    },
                },
            },
        },
    },
    "properties": {
        "manifest_format": {"const": "token-io-runtime-instructions-manifest/v1"},
        "policy_contract_version": {"const": 2},
        "legacy_context_index_version": {"const": 1},
        "legacy_source_hashes": {
            "type": "object",
            "additionalProperties": False,
            "required": ["registry_sha256", "context_index_sha256"],
            "properties": {
                "registry_sha256": {"$ref": "#/$defs/sha256"},
                "context_index_sha256": {"$ref": "#/$defs/sha256"},
                "owner_paths_sha256": {"$ref": "#/$defs/sha256"},
            },
        },
        "legacy_bindings": {
            "type": "object",
            "additionalProperties": False,
            "required": ["fragments", "owners"],
            "properties": {
                category: {
                    "type": "object",
                    "propertyNames": {"$ref": "#/$defs/stable_id"},
                    "additionalProperties": {"$ref": "#/$defs/stable_id"},
                }
                for category in ("fragments", "owners")
            },
        },
        "output_baseline_sha256": {"$ref": "#/$defs/sha256"},
        "budgets": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "artifact_bytes": {"type": "integer", "minimum": 1, "maximum": 8388608},
                "source_unit_records": {"type": "integer", "minimum": 1, "maximum": 512},
                "entry_closure_unicode_chars": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 262144,
                },
            },
        },
        "source_units": {
            "type": "array",
            "minItems": 1,
            "maxItems": 512,
            "items": {"$ref": "#/$defs/source_unit"},
        },
        "runtime_entries": {
            "type": "array",
            "minItems": 1,
            "maxItems": 512,
            "items": {"$ref": "#/$defs/runtime_entry"},
        },
        "owner_views": {
            "type": "array",
            "maxItems": 512,
            "items": {"$ref": "#/$defs/owner_view"},
        },
    },
}

# The standalone engine also accepts synthetic fixtures. Public compiler tools
# expose the stricter project contract; live legacy coverage is checked at run time.
PROJECT_MANIFEST_SCHEMA: dict[str, Any] = copy.deepcopy(MANIFEST_SCHEMA)
PROJECT_MANIFEST_SCHEMA["required"].append("legacy_bindings")
PROJECT_MANIFEST_SCHEMA["required"].append("owner_views")
PROJECT_MANIFEST_SCHEMA["properties"]["legacy_source_hashes"]["required"].append(
    "owner_paths_sha256"
)
PROJECT_MANIFEST_SCHEMA["$defs"]["runtime_entry"]["properties"]["branches"]["items"][
    "required"
].append("legacy_branch")
