"""Fixed, isolated reference-caller cases for the Issue 182 benchmark."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import time
from functools import cache
from pathlib import Path
from stat import S_ISREG
from typing import Any, Literal, TypedDict

from pydantic import BaseModel, ConfigDict, Field, StrictStr, create_model

DATASET_PATH = Path(__file__).resolve().parents[2] / "benchmarks" / "issue_182_cases.json"
DATASET = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
CASE_IDS = tuple(item["case_id"] for item in DATASET["cases"])
_CASES = {item["case_id"]: item for item in DATASET["cases"]}
_CALLER_MODEL = DATASET["model"]
_MAX_REPAIRS = 1
_EXPECTED_CONTENT = "## Facts\n\n- source fact\n"
_EXPECTED_CONTENT_BYTES = _EXPECTED_CONTENT.encode("utf-8")
_EXPECTED_CONTENT_SHA256 = "9513eb0120cd929326ec310b5293db744d3ab062c5b75e852fbb5ed2d1947b5c"
_COMMON_SOURCES = [
    "mcp/benchmarks/issue_182_cases.json",
    "mcp/tests/support/benchmark_cases.py",
    "mcp/tests/support/benchmark_metrics.py",
    "mcp/packages/token_io_decoupling_transport/src/token_io_decoupling_transport/tool_metadata.py",
]
_CASE_SOURCES = {
    "rules_current_verification": [
        "mcp/packages/token_io_decoupling_core/src/token_io_decoupling_core/rules.py",
        "mcp/rule-context-index.json",
        "mcp/packages/token_io_decoupling_transport/src/token_io_decoupling_transport/payloads.py",
        "docs/skill/references/coding/layer-02-workflow-concepts/verification-and-repair/verification.md",
    ],
    "multi_auto_work_definition": [
        "mcp/packages/token_io_decoupling_workflow/src/token_io_decoupling_workflow/workflow_routing.py",
        "docs/skill/references/coding/layer-04-workflows/coding-multi-agent.md",
        "docs/skill/references/coding/layer-04-workflows/modules/work-definition.md",
    ],
    "generic_create_preflight_pass": [
        "mcp/packages/token_io_decoupling_workflow/src/token_io_decoupling_workflow/compliance_preflight.py",
        "mcp/packages/token_io_decoupling_core/src/token_io_decoupling_core/compliance_core.py",
        "mcp/packages/token_io_decoupling_workflow/src/token_io_decoupling_workflow/tools.py",
        "mcp/CANDIDATE_COMPLIANCE.md",
    ],
    "skill_cross_language_preflight_fail": [
        "mcp/packages/token_io_decoupling_workflow/src/token_io_decoupling_workflow/compliance_preflight.py",
        "mcp/packages/token_io_decoupling_core/src/token_io_decoupling_core/compliance_core.py",
        "mcp/packages/token_io_decoupling_workflow/src/token_io_decoupling_workflow/tools.py",
        "mcp/CANDIDATE_COMPLIANCE.md",
    ],
    "primary_skill_fact_markdown_apply": [
        "mcp/packages/token_io_decoupling_workflow/src/token_io_decoupling_workflow/output_materialization.py",
        "mcp/packages/token_io_decoupling_workflow/src/token_io_decoupling_workflow/materialization_templates.py",
        "mcp/packages/token_io_decoupling_core/src/token_io_decoupling_core/materialization_models.py",
        "mcp/tests/unit_tests/test_output_materialization.py",
    ],
}


class _Judgment(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    outcome: StrictStr
    final_content: StrictStr = ""
    rationale: StrictStr


class _FileEffect(TypedDict):
    workflow_completed: bool | None
    workflow_completion_status: str
    workflow_completion_reason: str
    observed_content_sha256: str | None


@cache
def _case_judgment_model(case_id: str) -> type[_Judgment]:
    case = _CASES[case_id]
    choices = case["outcome_choices"]
    outcome_type: Any = Literal.__getitem__(tuple(choice["value"] for choice in choices))
    description = "\n".join(f"{choice['value']}: {choice['description']}" for choice in choices)
    return create_model(
        f"CaseJudgment_{case_id}",
        __base__=_Judgment,
        outcome=(outcome_type, Field(description=description)),
    )


def _json_bytes(value: object) -> int:
    return len(
        json.dumps(
            _jsonable(value), ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode()
    )


def _jsonable(value: object) -> object:
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        return model_dump(mode="json")
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _source_hashes(repo_root: Path, paths: list[str]) -> dict[str, Any]:
    result: dict[str, str] = {}
    unreadable: list[str] = []
    for relative in paths:
        path = repo_root / relative
        try:
            result[relative] = _sha(path.read_bytes())
        except OSError:
            unreadable.append(relative)
    return {
        "status": "unreadable" if unreadable else "readable",
        "hashes": result,
        "unreadable_paths": unreadable,
    }


def _source_hash_comparison(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    return {
        "before": before,
        "after": after,
        "stable": (
            before["status"] == "readable"
            and after["status"] == "readable"
            and before["hashes"] == after["hashes"]
        ),
    }


def _component_call(
    tool: str,
    arguments: object,
    result: object | None,
    seconds: float,
    status: str,
) -> dict[str, object | None]:
    return {
        "tool": tool,
        "arguments_utf8_bytes": _json_bytes({"payload": arguments}),
        "result_utf8_bytes": None if result is None else _json_bytes(result),
        "seconds": seconds,
        "status": status,
    }


def _execution_context(case_id: str, arm: str) -> dict[str, str | bool] | None:
    if case_id != "primary_skill_fact_markdown_apply":
        return None
    if arm == "baseline":
        return {
            "state_service": "not_used",
            "host_binding": "synthetic_fixture_not_used",
            "operator_grant": "synthetic_fixture_not_used",
            "effect_executor": "isolated_harness",
            "temporary_root": "isolated_per_case_arm",
            "production_authorization": False,
        }
    return {
        "state_service": "real_test_instance",
        "host_binding": "synthetic_test_fixture",
        "operator_grant": "synthetic_test_fixture",
        "effect_executor": "materialization_service",
        "temporary_root": "isolated_per_case_arm",
        "production_authorization": False,
    }


def _file_effect(root: Path, case_id: str) -> _FileEffect:
    if case_id != "primary_skill_fact_markdown_apply":
        return {
            "workflow_completed": False,
            "workflow_completion_status": "not_applicable",
            "workflow_completion_reason": "case_has_no_file_effect",
            "observed_content_sha256": None,
        }
    output_path = root / "project" / "docs" / "skill-output.md"
    try:
        file_stat = output_path.stat()
    except FileNotFoundError:
        return {
            "workflow_completed": False,
            "workflow_completion_status": "not_applied",
            "workflow_completion_reason": "target_file_absent",
            "observed_content_sha256": None,
        }
    except OSError:
        return {
            "workflow_completed": None,
            "workflow_completion_status": "unknown",
            "workflow_completion_reason": "target_file_unreadable",
            "observed_content_sha256": None,
        }
    if not S_ISREG(file_stat.st_mode):
        return {
            "workflow_completed": False,
            "workflow_completion_status": "not_applied",
            "workflow_completion_reason": "target_is_not_a_file",
            "observed_content_sha256": None,
        }
    try:
        actual_bytes = output_path.read_bytes()
    except OSError:
        return {
            "workflow_completed": None,
            "workflow_completion_status": "unknown",
            "workflow_completion_reason": "target_file_unreadable",
            "observed_content_sha256": None,
        }
    actual_sha256 = _sha(actual_bytes)
    matches = actual_bytes == _EXPECTED_CONTENT_BYTES and actual_sha256 == _EXPECTED_CONTENT_SHA256
    return {
        "workflow_completed": matches,
        "workflow_completion_status": "complete" if matches else "content_mismatch",
        "workflow_completion_reason": "exact_frozen_content_present"
        if matches
        else "target_bytes_do_not_match_frozen_content",
        "observed_content_sha256": actual_sha256,
    }


def _service_metadata(service: str) -> tuple[dict[str, object], list[str]]:
    from token_io_decoupling_transport.tool_metadata import tool_description

    if service == "rule_context":
        from token_io_decoupling_transport.payloads import RuleContextPayload

        tool = "rules_get_context"
        schema = RuleContextPayload
        schema_source = (
            "mcp/packages/token_io_decoupling_transport/src/token_io_decoupling_transport/"
            "payloads.py"
        )
    elif service == "workflow_routing":
        from token_io_decoupling_workflow.workflow_routing import WorkflowRoutingPayload

        tool = "decide_decoupling_workflow"
        schema = WorkflowRoutingPayload
        schema_source = (
            "mcp/packages/token_io_decoupling_workflow/src/token_io_decoupling_workflow/"
            "workflow_routing.py"
        )
    elif service == "candidate_compliance":
        from token_io_decoupling_workflow.tools import _COMPLIANCE_PREFLIGHT

        tool = "validate_decoupling_compliance"
        schema = _COMPLIANCE_PREFLIGHT
        schema_source = (
            "mcp/packages/token_io_decoupling_workflow/src/token_io_decoupling_workflow/tools.py"
        )
    else:
        from token_io_decoupling_core.materialization_models import (
            MaterializeDecoupledOutputPayload,
        )

        tool = "materialize_decoupled_output"
        schema = MaterializeDecoupledOutputPayload
        schema_source = (
            "mcp/packages/token_io_decoupling_core/src/token_io_decoupling_core/"
            "materialization_models.py"
        )
    schema_json = schema.model_json_schema()
    metadata = {"tool": tool, "description": tool_description(tool), "input_schema": schema_json}
    source_paths = [
        "mcp/packages/token_io_decoupling_transport/src/token_io_decoupling_transport/tool_metadata.py",
        schema_source,
    ]
    return metadata, source_paths


def _case_prompt(case: dict[str, Any], evidence: object, *, assisted: bool) -> str:
    payload: dict[str, object] = {
        "question": case["question"],
        "verified_facts": case["facts"],
        "evidence": evidence,
        "outcome_choices": case["outcome_choices"],
        "output_contract": {
            "outcome": "exactly one value from the case-specific outcome choices",
            "final_content": "candidate content only for the materialization case; otherwise empty",
        },
    }
    if case["service"] == "materialization":
        payload["materialization_contract"] = {
            "template": case["template_contract"],
        }
    if assisted:
        metadata, _ = _service_metadata(case["service"])
        payload["actual_tool_metadata_and_input_schema"] = metadata
    return (
        "Answer this fixed benchmark question using only the supplied verified facts and evidence. "
        "Treat each listed outcome branch as mutually exclusive, and do not infer unlisted states. "
        "A structural preflight result is not final Verification, and a route suggestion is not "
        "authorization. Return the requested structured judgment.\n"
        + json.dumps(_jsonable(payload), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    )


def _judgment_matches_case(judgment: _Judgment, case: dict[str, Any]) -> bool:
    if judgment.outcome != case["expected"]:
        return False
    if case["service"] == "materialization":
        content = judgment.final_content.encode("utf-8")
        return content == _EXPECTED_CONTENT_BYTES and _sha(content) == _EXPECTED_CONTENT_SHA256
    return judgment.final_content == ""


def _call_judge(
    recorder: Any, case_id: str, arm: str, case: dict[str, Any], evidence: object
) -> tuple[_Judgment, int, list[str], float]:
    from openai import OpenAIError

    client = recorder.make_client(case_id=case_id, arm=arm, component="caller", timeout=30.0)
    judgment_model = _case_judgment_model(case_id)
    prompt = _case_prompt(case, evidence, assisted=arm == "assisted")
    request_fingerprint = {
        "prompt": prompt,
        "text_format_schema": judgment_model.model_json_schema(),
        "model": _CALLER_MODEL,
        "reasoning_effort": DATASET["reasoning_effort"],
    }
    prompt_hashes = [
        _sha(
            json.dumps(
                request_fingerprint, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            ).encode()
        )
    ]
    start = time.perf_counter()
    repairs = 0
    judgment: _Judgment | None = None
    try:
        previous_outcome: str | None = None
        for attempt in range(_MAX_REPAIRS + 1):
            request_input = prompt
            if attempt:
                repairs += 1
                repair_scope = (
                    "outcome and exact final content"
                    if case["service"] == "materialization"
                    else "outcome and the empty final-content requirement"
                )
                request_input += (
                    "\nRepair the prior semantic judgment using the same evidence. Re-check "
                    f"{repair_scope}; prior outcome was {previous_outcome!r}. "
                    "Do not add facts or repeat an API error."
                )
                repair_fingerprint = {**request_fingerprint, "prompt": request_input}
                prompt_hashes.append(
                    _sha(
                        json.dumps(
                            repair_fingerprint,
                            ensure_ascii=False,
                            sort_keys=True,
                            separators=(",", ":"),
                        ).encode()
                    )
                )
            response = client.responses.parse(
                model=_CALLER_MODEL,
                input=request_input,
                text_format=judgment_model,
                store=False,
                reasoning={"effort": DATASET["reasoning_effort"]},
                max_output_tokens=4_000,
                truncation="disabled",
                tools=[],
            )
            parsed = getattr(response, "output_parsed", None)
            if (
                type(parsed) is judgment_model
                and getattr(response, "status", "completed") == "completed"
            ):
                judgment = parsed
                if _judgment_matches_case(judgment, case):
                    break
                previous_outcome = judgment.outcome
        if judgment is None:
            raise ValueError("caller_structured_output_invalid")
    except OpenAIError as exc:
        raise RuntimeError("caller_provider_error") from exc
    finally:
        close = getattr(client, "close", None)
        if callable(close):
            close()
    return judgment, repairs, prompt_hashes, time.perf_counter() - start


def _rule_service(
    case_id: str, arm: str, repo_root: Path, recorder: Any
) -> tuple[Any, dict[str, float]]:
    from token_io_decoupling_core.rules import RuleLoader

    start = time.perf_counter()
    loader = RuleLoader(repository_root=repo_root)
    if arm == "baseline":
        context = loader.load_context("verification")
        return context, {"service": time.perf_counter() - start}
    bundle = loader.load_context_bundle("verification", fragment_ids=["verification.actions"])
    return bundle, {"service": time.perf_counter() - start}


def _routing_service(
    case_id: str, arm: str, repo_root: Path, recorder: Any
) -> tuple[Any, dict[str, float]]:
    from token_io_decoupling_workflow.decisions import DecisionsRuntimeConfig
    from token_io_decoupling_workflow.workflow_routing import (
        CodingMode,
        DecouplingWorkflowRequest,
        RoutingSourceFact,
        WorkflowRouter,
        source_facts_hash,
    )

    facts = [
        RoutingSourceFact(
            fact_id=f"fact-{index + 1}",
            source_ref=f"case:fact-{index + 1}",
            statement=statement,
        )
        for index, statement in enumerate(_CASES[case_id]["facts"])
    ]
    request = DecouplingWorkflowRequest.model_validate(
        {
            "task_id": "issue-182-benchmark-multi-work-definition",
            "task_summary": "Suggest the current stage in a locked Multi-Agent Coding route.",
            "stage": "auto",
            "language": "en",
            "mode_locked": True,
            "mode_count": {"mode": CodingMode.MULTI_AGENT, "child_count": 1},
            "capabilities": [
                {
                    "capability_id": "rule_context",
                    "status": "available",
                    "source_ref": "case:verified",
                },
                {
                    "capability_id": "implementation",
                    "status": "available",
                    "source_ref": "case:verified",
                },
            ],
            "hard_constraints": [],
            "source_facts": facts,
            "source_facts_hash": source_facts_hash(facts),
            "outbound_data_permitted": True,
        }
    )
    if arm == "baseline":
        start = time.perf_counter()
        baseline_sources = [
            "docs/skill/references/coding/layer-04-workflows/coding-multi-agent.md",
            "docs/skill/references/coding/layer-04-workflows/modules/work-definition.md",
        ]
        evidence = {
            source: (repo_root / source).read_text(encoding="utf-8") for source in baseline_sources
        }
        return {
            "request": request.model_dump(mode="json"),
            "full_l4_source": evidence,
        }, {"service": time.perf_counter() - start}
    from token_io_decoupling_core.rules import RuleLoader

    router = WorkflowRouter(
        RuleLoader(repository_root=repo_root),
        DecisionsRuntimeConfig(enabled=True, outbound_data_permitted=True),
        client_factory=lambda key, url: recorder.make_client(
            case_id=case_id, arm=arm, component="inner", timeout=20.0
        ),
    )
    start = time.perf_counter()
    result = router.decide(request)
    return {"request": request.model_dump(mode="json"), "result": result.model_dump(mode="json")}, {
        "service": time.perf_counter() - start
    }


def _preflight_service(
    case_id: str, arm: str, case_id_path: Path, kind: str, repo_root: Path
) -> tuple[Any, dict[str, float]]:
    if kind == "generic":
        candidates = [
            {
                "path": "artifacts/summary.txt",
                "operation": "create",
                "baseline": {"state": "absent"},
                "content": "verified summary\n",
            }
        ]
        scope = "generic_project"
    else:
        en_path = (
            "docs/skill/references/coding/layer-01-fundamental-concepts/"
            "execution-planning/benchmark.md"
        )
        zh_path = (
            "docs/skill/references/coding/layer-01-fundamental-concepts/"
            "execution-planning/benchmark_zh_cn.md"
        )
        english = (
            f"[English]({Path(en_path).name}) | [简体中文]({Path(zh_path).name})\n\n"
            "# Owner\n\n## General rules\nRules.\n\n"
            "## Codex CLI / ChatGPT Desktop optimizations\nNone.\n\n"
            "## Claude Code CLI / Claude Desktop optimizations\nNone.\n\n"
            f"## Related concepts\n- [Invalid cross-language target]({Path(zh_path).name})\n"
        )
        chinese = (
            f"[English]({Path(en_path).name}) | [简体中文]({Path(zh_path).name})\n\n"
            "# Owner\n\n## 通用规范\n规范。\n\n"
            "## Codex CLI / ChatGPT Desktop 特别优化指令\n无。\n\n"
            "## Claude Code CLI / Claude Desktop 特别优化指令\n无。\n\n"
            "## 相关概念\n无。\n"
        )
        candidates = [
            {
                "path": en_path,
                "operation": "create",
                "baseline": {"state": "absent"},
                "content": english,
            },
            {
                "path": zh_path,
                "operation": "create",
                "baseline": {"state": "absent"},
                "content": chinese,
            },
        ]
        scope = "skill_maintenance"
    request = {"policy_scope": scope, "candidates": candidates}
    start = time.perf_counter()
    if arm == "baseline":
        policy = (repo_root / "mcp" / "CANDIDATE_COMPLIANCE.md").read_text(encoding="utf-8")
        return {
            "request": request,
            "full_policy_context": policy,
            "trusted_root_facts": {
                "candidate_targets_absent": True,
                "candidate_paths_bounded": True,
            },
        }, {"service": time.perf_counter() - start}
    from token_io_decoupling_workflow.compliance_preflight import (
        CompliancePreflightService,
        validate_decoupling_compliance,
    )

    service = CompliancePreflightService(case_id_path, {"generic_project", "skill_maintenance"})
    result = validate_decoupling_compliance(service, request)
    elapsed = time.perf_counter() - start
    service.close()
    return {"result": result, "request": request}, {"service": elapsed}


def _materialization_service(
    case_id: str,
    arm: str,
    root: Path,
    repo_root: Path,
    recorder: Any,
    component_calls: list[dict[str, object]] | None = None,
) -> tuple[Any, dict[str, float], str]:
    if component_calls is None:
        component_calls = []
    component_calls_start = len(component_calls)
    setup_started = time.perf_counter()
    case = _CASES[case_id]
    from token_io_decoupling_core.materialization_models import (
        FactHeading,
        FactMarkdownTemplate,
        MaterializationApplyRequest,
        MaterializationInspectRequest,
        MaterializationPrepareRequest,
        SourceFact,
    )
    from token_io_decoupling_core.workflow_models import OutputClass

    fixture_path = repo_root / "mcp" / "tests" / "unit_tests" / "test_output_materialization.py"
    spec = importlib.util.spec_from_file_location(
        "_issue_182_materialization_fixture", fixture_path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("materialization_fixture_unavailable")
    fixture_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixture_module)
    _workspace = fixture_module._workspace

    path = "docs/skill-output.md"
    project, artifacts, state, _provider, preflight, _grant, _config, materializer = _workspace(
        root, [path], output_class=OutputClass.SKILL_INSTRUCTIONS
    )
    # Test-only recorder hook; production has no public client override.
    materializer._renderer._make_client = lambda key, url: recorder.make_client(
        case_id=case_id, arm=arm, component="inner", timeout=30.0
    )
    template_contract = case["template_contract"]
    template = FactMarkdownTemplate(
        kind=template_contract["kind"],
        ordering=template_contract["ordering"],
        headings=[FactHeading(**heading) for heading in template_contract["headings"]],
        facts=[SourceFact(**fact) for fact in template_contract["facts"]],
    )
    setup_elapsed = time.perf_counter() - setup_started
    prepare_started = time.perf_counter()
    prepare_request = MaterializationPrepareRequest.model_validate(
        {
            "action": "prepare",
            "files": [
                {
                    "path": path,
                    "operation": "create",
                    "baseline": {"state": "absent"},
                    "template": template,
                }
            ],
            "outbound_data_permitted": True,
        }
    )
    try:
        prepared = materializer.execute(prepare_request)
    except Exception:
        component_calls.append(
            _component_call(
                "materialize_decoupled_output",
                {"request": prepare_request},
                None,
                time.perf_counter() - prepare_started,
                "unknown",
            )
        )
        raise
    prepare_elapsed = time.perf_counter() - prepare_started
    component_calls.append(
        _component_call(
            "materialize_decoupled_output",
            {"request": prepare_request},
            prepared,
            prepare_elapsed,
            str(prepared.get("status", "unknown")),
        )
    )
    if prepared.get("status") != "prepared":
        materializer.close()
        preflight.close()
        return (
            {"prepare": prepared, "component_calls": component_calls[component_calls_start:]},
            {"setup": setup_elapsed, "service": prepare_elapsed, "apply": 0.0},
            "",
        )
    prepared_id = str(prepared["prepared_id"])
    manifest = str(prepared["manifest_sha256"])
    inspect_request = MaterializationInspectRequest(
        action="inspect",
        prepared_id=prepared_id,
        expected_manifest_hash=manifest,
        file_index=0,
        max_chars=8192,
    )
    inspect_started = time.perf_counter()
    try:
        inspected = materializer.execute(inspect_request)
    except Exception:
        component_calls.append(
            _component_call(
                "materialize_decoupled_output",
                {"request": inspect_request},
                None,
                time.perf_counter() - inspect_started,
                "unknown",
            )
        )
        raise
    inspect_elapsed = time.perf_counter() - inspect_started
    component_calls.append(
        _component_call(
            "materialize_decoupled_output",
            {"request": inspect_request},
            inspected,
            inspect_elapsed,
            str(inspected.get("status", "unknown")),
        )
    )
    expected_content = _EXPECTED_CONTENT
    review_ok = inspected.get("content") == expected_content and inspected.get("complete") is True
    preflight_started = time.perf_counter()
    applied: dict[str, Any] = {"status": "blocked", "reason_code": "candidate_review_mismatch"}
    apply_elapsed = 0.0
    if review_ok:
        apply_request = MaterializationApplyRequest(
            action="apply", prepared_id=prepared_id, expected_manifest_hash=manifest
        )
        try:
            applied = materializer.execute(apply_request)
        except Exception:
            component_calls.append(
                _component_call(
                    "materialize_decoupled_output",
                    {"request": apply_request},
                    None,
                    time.perf_counter() - preflight_started,
                    "unknown",
                )
            )
            raise
        apply_elapsed = time.perf_counter() - preflight_started
        component_calls.append(
            _component_call(
                "materialize_decoupled_output",
                {"request": apply_request},
                applied,
                apply_elapsed,
                str(applied.get("status", "unknown")),
            )
        )
    actual = (project / path).read_text(encoding="utf-8") if (project / path).exists() else None
    result = {
        "prepare": prepared,
        "inspect": inspected,
        "apply": applied,
        "actual_content": actual,
        "component_calls": component_calls[component_calls_start:],
    }
    materializer.close()
    preflight.close()
    return (
        result,
        {
            "setup": setup_elapsed,
            "service": prepare_elapsed + inspect_elapsed,
            "apply": apply_elapsed,
        },
        expected_content,
    )


def _baseline_materialization(root: Path, content: str) -> str:
    output = root / "project" / "docs" / "skill-output.md"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(content.encode("utf-8"))
    return output.read_bytes().decode("utf-8")


def run_case(
    case_id: str,
    arm: str,
    recorder: Any,
    repo_root: str | os.PathLike[str],
    temporary_root: str | os.PathLike[str],
) -> dict[str, Any]:
    """Run one frozen case/arm in its own temporary root; never calls APIs except via recorder."""
    if case_id not in _CASES or arm not in {"baseline", "assisted"}:
        raise ValueError("benchmark_case_or_arm_invalid")
    start_all = time.perf_counter()
    case = _CASES[case_id]
    repo = Path(repo_root).resolve(strict=True)
    root = Path(temporary_root).resolve() / case_id / arm
    if root == repo or repo in root.parents or root in repo.parents:
        raise ValueError("benchmark_temporary_root_must_be_isolated")
    root.mkdir(parents=True, exist_ok=False)
    if arm == "assisted":
        os.chmod(root, 0o700)
    calls_start = len(getattr(recorder, "calls", []))
    attempts_start = int(getattr(recorder, "http_attempts", 0))
    service_payload: Any = {"verified_facts": case["facts"]}
    component_calls: list[dict[str, object]] = []
    timings: dict[str, float] = {
        "setup": time.perf_counter() - start_all,
        "caller": 0.0,
        "service": 0.0,
        "harness": 0.0,
        "apply": 0.0,
    }
    expected = case["expected"]
    final_content = ""
    source_paths = list(dict.fromkeys(_COMMON_SOURCES + _CASE_SOURCES[case_id]))
    source_hashes_before = _source_hashes(repo, source_paths)
    metadata_hash = ""
    failure_category: str | None = None
    observed_content_sha256: str | None = None
    service_status = "not_run"
    try:
        service = case["service"]
        if case_id == "rules_current_verification":
            service_payload, extra = _rule_service(case_id, arm, repo, recorder)
            timings.update(extra)
            service_status = "available" if arm == "assisted" else "reference_context_loaded"
            if arm == "assisted":
                component_calls.append(
                    _component_call(
                        "rules_get_context",
                        {
                            "node_id": "verification",
                            "context_version": 1,
                            "fragment_ids": ["verification.actions"],
                        },
                        service_payload,
                        timings.get("service", 0.0),
                        service_status,
                    )
                )
        elif case_id == "multi_auto_work_definition":
            service_payload, extra = _routing_service(case_id, arm, repo, recorder)
            timings.update(extra)
            route_result = (
                service_payload.get("result", {}) if isinstance(service_payload, dict) else {}
            )
            service_status = (
                str(route_result.get("status", "available"))
                if isinstance(route_result, dict)
                else "available"
            )
            if arm == "assisted":
                component_calls.append(
                    _component_call(
                        "decide_decoupling_workflow",
                        {"request": service_payload.get("request", {})},
                        service_payload.get("result", {}),
                        timings.get("service", 0.0),
                        service_status,
                    )
                )
        elif case_id in {"generic_create_preflight_pass", "skill_cross_language_preflight_fail"}:
            service_root = root / "project"
            service_root.mkdir()
            kind = "generic" if case_id == "generic_create_preflight_pass" else "skill"
            service_payload, extra = _preflight_service(case_id, arm, service_root, kind, repo)
            timings.update(extra)
            if arm == "assisted":
                result = service_payload["result"]
                service_status = str(result.get("status", "unknown"))
                component_calls.append(
                    {
                        "tool": "validate_decoupling_compliance",
                        "arguments_utf8_bytes": _json_bytes(
                            {"payload": {"request": service_payload["request"]}}
                        ),
                        "result_utf8_bytes": _json_bytes(result),
                        "seconds": timings.get("service", 0.0),
                        "status": service_status,
                    }
                )
            else:
                service_status = "reference_context_loaded"
        else:
            if arm == "baseline":
                service_payload = {
                    "verified_facts": case["facts"],
                    "baseline_harness_write": "pending caller output",
                }
                service_status = "caller_pending"
            else:
                service_payload, extra, final_content = _materialization_service(
                    case_id, arm, root, repo, recorder, component_calls
                )
                timings.update(extra)
                applied = service_payload.get("apply", {})
                service_status = str(applied.get("status", "blocked"))
        if service in {
            "rule_context",
            "workflow_routing",
            "candidate_compliance",
            "materialization",
        }:
            metadata, _metadata_sources = _service_metadata(service)
            metadata_hash = _sha(
                json.dumps(
                    metadata, ensure_ascii=False, sort_keys=True, separators=(",", ":")
                ).encode()
            )
        if case_id == "primary_skill_fact_markdown_apply" and arm == "assisted":
            caller_evidence = {
                "metadata_hash": metadata_hash,
                **service_payload,
            }
        else:
            caller_evidence = (
                service_payload
                if arm == "assisted"
                else {"full_verified_facts": case["facts"], "source_material": service_payload}
            )
            if case_id == "primary_skill_fact_markdown_apply":
                caller_evidence = {
                    "verified_facts": case["facts"],
                    "template_contract": case["template_contract"],
                    "rendering_contract": case["template_contract"]["format"],
                }
        judgment, repair_count, prompt_hashes, caller_elapsed = _call_judge(
            recorder, case_id, arm, case, caller_evidence
        )
        timings["caller"] = caller_elapsed
        observed = judgment.outcome
        semantic_success = observed == expected
        if case["service"] == "candidate_compliance":
            if arm == "assisted":
                semantic_success = semantic_success and service_status == expected
        elif case["service"] == "workflow_routing":
            route_result = (
                service_payload.get("result", {}) if isinstance(service_payload, dict) else {}
            )
            semantic_success = (
                semantic_success
                and isinstance(route_result, dict)
                and (route_result.get("module_id") == expected if arm == "assisted" else True)
            )
        if case_id == "primary_skill_fact_markdown_apply":
            if arm == "baseline":
                harness_start = time.perf_counter()
                final_content = judgment.final_content
                if final_content.encode("utf-8") == _EXPECTED_CONTENT_BYTES:
                    final_content = _baseline_materialization(root, final_content)
                    service_status = "harness_written"
                else:
                    service_status = "candidate_mismatch"
                timings["harness"] = time.perf_counter() - harness_start
        file_effect = _file_effect(root, case_id)
        if case_id == "primary_skill_fact_markdown_apply":
            observed_content_sha256 = file_effect["observed_content_sha256"]
            content_oracle_passes = file_effect["workflow_completed"] is True
            if arm == "baseline":
                semantic_success = (
                    semantic_success
                    and service_status == "harness_written"
                    and content_oracle_passes
                )
            else:
                actual_content = service_payload.get("actual_content")
                semantic_success = (
                    semantic_success
                    and service_status in {"applied", "already_identical"}
                    and isinstance(actual_content, str)
                    and actual_content.encode("utf-8") == _EXPECTED_CONTENT_BYTES
                    and _sha(actual_content.encode("utf-8")) == _EXPECTED_CONTENT_SHA256
                    and content_oracle_passes
                )
        workflow_completed = file_effect["workflow_completed"]
        source_hashes_after = _source_hashes(repo, source_paths)
        source_hashes = _source_hash_comparison(source_hashes_before, source_hashes_after)
        semantic_success = semantic_success and source_hashes["stable"]
        calls = list(getattr(recorder, "calls", []))[calls_start:]
        return {
            "case_id": case_id,
            "arm": arm,
            "expected": expected,
            "observed": observed,
            "semantic_success": semantic_success,
            "first_attempt_success": semantic_success and repair_count == 0,
            "repair_count": repair_count,
            "service_status": service_status,
            "workflow_completed": workflow_completed,
            "workflow_completion_status": file_effect["workflow_completion_status"],
            "workflow_completion_reason": file_effect["workflow_completion_reason"],
            "failure_category": failure_category,
            "component_calls": component_calls,
            "api_calls": calls,
            "http_attempts": int(getattr(recorder, "http_attempts", 0)) - attempts_start,
            "timings": {**timings, "elapsed": time.perf_counter() - start_all},
            "metadata_hash": metadata_hash,
            "prompt_hashes": {
                f"caller_{index + 1}": value for index, value in enumerate(prompt_hashes)
            },
            "source_hashes": source_hashes,
            "expected_content_sha256": _EXPECTED_CONTENT_SHA256
            if case_id == "primary_skill_fact_markdown_apply"
            else None,
            "observed_content_sha256": observed_content_sha256,
            "execution_context": _execution_context(case_id, arm),
        }
    except Exception as exc:
        # Keep provider/service failures bounded and omit exception text/credentials.
        failure_category = (
            "caller_provider_error"
            if isinstance(exc, RuntimeError) and str(exc) == "caller_provider_error"
            else type(exc).__name__
            if type(exc).__name__ in {"TimeoutError", "ValueError"}
            else "benchmark_case_error"
        )
        file_effect = _file_effect(root, case_id)
        return {
            "case_id": case_id,
            "arm": arm,
            "expected": expected,
            "observed": None,
            "semantic_success": False,
            "first_attempt_success": False,
            "repair_count": 0,
            "service_status": service_status,
            "workflow_completed": file_effect["workflow_completed"],
            "workflow_completion_status": file_effect["workflow_completion_status"],
            "workflow_completion_reason": file_effect["workflow_completion_reason"],
            "failure_category": failure_category,
            "component_calls": component_calls,
            "api_calls": list(getattr(recorder, "calls", []))[calls_start:],
            "http_attempts": int(getattr(recorder, "http_attempts", 0)) - attempts_start,
            "timings": {**timings, "elapsed": time.perf_counter() - start_all},
            "metadata_hash": metadata_hash,
            "prompt_hashes": {},
            "source_hashes": _source_hash_comparison(
                source_hashes_before, _source_hashes(repo, source_paths)
            ),
            "execution_context": _execution_context(case_id, arm),
            "observed_content_sha256": file_effect["observed_content_sha256"],
        }
