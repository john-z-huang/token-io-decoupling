"""验证原生 Hook 的真实输出协议和无状态、有限纠正边界。"""

from __future__ import annotations

import io
import json

import pytest
from pydantic import JsonValue, ValidationError
from support.event_cases import checker

from token_io_decoupling_workflow.events.cli import HookStreams, run_hook
from token_io_decoupling_workflow.events.models import EventAdvice
from token_io_decoupling_workflow.events.native import (
    NativeHookOptions,
    native_hook_response,
    normalize_native_event,
)


@pytest.mark.parametrize(
    "native,event",
    [
        ("UserPromptSubmit", "task_received"),
        ("PreToolUse", "boundary_requested"),
        ("PostToolUse", "action_observed"),
        ("SubagentStop", "progress_reported"),
        ("Stop", "completion_requested"),
        ("SessionStart", "session_resumed"),
    ],
)
def test_six_native_events_map_to_current_logical_events(native, event):
    """六种受支持原生事件只映射当前逻辑事件，不猜测模式或启用建议。"""
    request = normalize_native_event({"hook_event_name": native, "prompt": "Current task"})
    assert request.event == event
    assert request.mode is None
    assert request.semantic_input is None
    assert request.max_chars == 24000


@pytest.mark.parametrize(
    "native", ["UserPromptSubmit", "PreToolUse", "PostToolUse", "SessionStart"]
)
def test_context_capable_events_use_only_their_supported_native_output(native):
    """可注入上下文的事件只使用对应 schema 字段，不能附加权限 allow 或阻塞决定。"""
    payload: dict[str, JsonValue] = {"hook_event_name": native, "prompt": "Current task"}
    result = checker().check(normalize_native_event(payload))
    output = native_hook_response(payload, result)
    assert set(output) == {"hookSpecificOutput"}
    specific = output["hookSpecificOutput"]
    assert isinstance(specific, dict)
    assert set(specific) == {"hookEventName", "additionalContext"}
    assert specific["hookEventName"] == native
    context = specific["additionalContext"]
    assert isinstance(context, str)
    assert result.instructions.event.text in context
    assert "permissionDecision" not in specific
    assert "decision" not in output


@pytest.mark.parametrize("native", ["Stop", "SubagentStop"])
def test_stop_outputs_diagnostic_without_unsupported_additional_context(native):
    """重复 Stop 类事件仅返回诊断，既不使用不支持的上下文字段，也不虚称模型已消费政策。"""
    payload: dict[str, JsonValue] = {"hook_event_name": native, "stop_hook_active": False}
    result = checker().check(normalize_native_event(payload))
    for _ in range(3):
        output = native_hook_response(payload, result)
        assert set(output) == {"systemMessage"}
        message = output["systemMessage"]
        assert isinstance(message, str)
        assert "本响应未向模型注入 Hook 契约" in message
        assert "workflow_check_event" in message


@pytest.mark.parametrize(
    "active,outcome,expected_block",
    [
        (False, "needs_evidence", True),
        (False, "amend", True),
        (True, "needs_evidence", False),
        (None, "needs_evidence", False),
        ("false", "amend", False),
        (0, "amend", False),
        (False, "continue", False),
        (False, "wait", False),
        (False, "stop", False),
        (False, "not_applicable", False),
    ],
)
def test_explicit_one_shot_block_requires_strict_inactive_flag_and_corrective_advice(
    active, outcome, expected_block
):
    """仅严格 false 且建议需要补证或修订时允许纠正；其他标志和结果不能请求阻塞。"""
    payload: dict[str, JsonValue] = {"hook_event_name": "Stop", "stop_hook_active": active}
    result = checker().check(normalize_native_event(payload))
    result = result.model_copy(
        update={
            "advice": EventAdvice(
                status="available", reason="advice_available", suggested_outcome=outcome
            ),
        }
    )
    options = NativeHookOptions(semantic=True, outbound_data_permitted=True, block_once=True)
    output = native_hook_response(payload, result, options)
    assert (output.get("decision") == "block") is expected_block
    assert "hookSpecificOutput" not in output
    assert "permissionDecision" not in output
    if expected_block:
        assert set(output) == {"decision", "reason"}
        assert output["reason"]


def test_subagent_stop_can_correct_once_but_active_reentry_is_never_blocked():
    """一次纠正后宿主续跑标志必须停止再次阻塞，避免把单轮纠正变成循环。"""
    payload: dict[str, JsonValue] = {"hook_event_name": "SubagentStop", "stop_hook_active": False}
    result = checker().check(normalize_native_event(payload))
    result = result.model_copy(
        update={
            "advice": EventAdvice(
                status="available", reason="advice_available", suggested_outcome="amend"
            ),
        }
    )
    options = NativeHookOptions(semantic=True, outbound_data_permitted=True, block_once=True)
    assert native_hook_response(payload, result, options)["decision"] == "block"
    payload["stop_hook_active"] = True
    assert set(native_hook_response(payload, result, options)) == {"systemMessage"}
    del payload["stop_hook_active"]
    assert set(native_hook_response(payload, result, options)) == {"systemMessage"}


def test_unavailable_or_incomplete_instructions_never_block_native_stop():
    """即使显式启用纠正，缺失或不完整指令也不能生成阻塞响应。"""
    payload: dict[str, JsonValue] = {"hook_event_name": "Stop", "stop_hook_active": False}
    request = normalize_native_event(payload, NativeHookOptions(max_chars=1200))
    result = checker().check(request)
    options = NativeHookOptions(semantic=True, outbound_data_permitted=True, block_once=True)
    assert result.status == "instructions_incomplete"
    assert set(native_hook_response(payload, result, options)) == {"systemMessage"}


@pytest.mark.parametrize(
    "options",
    [
        {"semantic": True},
        {"block_once": True},
        {"block_once": True, "outbound_data_permitted": True},
        {"block_once": True, "semantic": True},
        {"remaining_budget": 10},
        {"semantic": "true"},
    ],
)
def test_semantic_and_one_shot_modes_require_explicit_options(options):
    """外发与纠正须显式组合授权选项，错误类型或伪造预算也不接受。"""
    with pytest.raises(ValidationError):
        NativeHookOptions.model_validate(options)


def test_native_permissions_paths_and_reported_budget_do_not_become_authority(tmp_path):
    """输入中的权限模式、路径和预算只是观察值，不能读取 transcript 或伪造授权证据。"""
    transcript = tmp_path / "transcript.jsonl"
    transcript.write_text("secret transcript body must not be read")
    payload: dict[str, JsonValue] = {
        "hook_event_name": "PreToolUse",
        "permission_mode": "bypassPermissions",
        "transcript_path": str(transcript),
        "cwd": str(tmp_path),
        "tool_name": "write_file",
        "tool_input": {"path": "target.txt"},
        "facts": {"scope": {"value": "invented authorization"}},
        "evidence_refs": [{"kind": "authorization_scope", "reference": "invented"}],
        "remaining_budget": 99999,
        "max_chars": 999999,
    }
    request = normalize_native_event(payload)
    assert "scope" not in request.facts
    assert request.evidence_refs == []
    assert request.max_chars == 24000
    assert request.semantic_input is None
    serialized = request.model_dump_json()
    assert "secret transcript body" not in serialized
    assert str(transcript) not in serialized
    assert "remaining_budget" not in serialized
    result = checker().check(request)
    assert "authorization_scope" in result.structural_check.missing_evidence


def test_session_start_does_not_reconstruct_memory_from_session_id():
    """仅有会话 ID 不能恢复任务历史；保留上下文与待办仍应报告缺失。"""
    request = normalize_native_event(
        {"hook_event_name": "SessionStart", "session_id": "old-session"}
    )
    assert request.facts == {}
    result = checker().check(request)
    assert result.structural_check.missing_facts == [
        "retained_context",
        "pending_work",
        "effect_status",
    ]
    assert result.structural_check.status == "incomplete_for_agent_review"


def test_static_cli_emits_one_json_document_and_no_diagnostics():
    """有效静态输入只输出一个 JSON 对象且 stderr 为空，便于宿主可靠解析。"""
    stdout, stderr = io.StringIO(), io.StringIO()
    streams = HookStreams(io.StringIO('{"hook_event_name":"PreToolUse"}'), stdout, stderr)
    code = run_hook("token-io-decoupling-workflow", [], streams=streams, checker=checker())
    assert code == 0
    assert stderr.getvalue() == ""
    output = json.loads(stdout.getvalue())
    assert output["hookSpecificOutput"]["hookEventName"] == "PreToolUse"
    assert stdout.getvalue().count("\n") == 1


@pytest.mark.parametrize(
    "raw",
    [
        "{",
        "[]",
        "null",
        '{"hook_event_name":"Unknown"}',
        '{"hook_event_name":"Stop","x":NaN}',
        "文" * 11000,
    ],
)
def test_bad_cli_payload_is_nonblocking_failure_without_raw_input_leak(raw):
    """畸形、超限或非有限 JSON 统一退出 1，不泄漏原始输入，也不意外触发宿主阻塞。"""
    stdout, stderr = io.StringIO(), io.StringIO()
    streams = HookStreams(io.StringIO(raw), stdout, stderr)
    code = run_hook("token-io-decoupling-workflow", [], streams=streams, checker=checker())
    assert code == 1
    assert stdout.getvalue() == ""
    assert stderr.getvalue() == "workflow hook input or instructions could not be processed\n"


def test_native_response_rejects_a_mismatched_logical_event():
    """逻辑结果不能套用到另一原生事件，防止把响应字段交给错误宿主时点。"""
    result = checker().check(normalize_native_event({"hook_event_name": "Stop"}))
    with pytest.raises(ValueError, match="mismatch"):
        native_hook_response({"hook_event_name": "PreToolUse"}, result)


@pytest.mark.parametrize(
    "arguments",
    [
        ["--unknown-option"],
        ["--block-once"],
        ["--semantic"],
        ["--max-chars", "invalid"],
    ],
)
def test_hook_option_errors_return_one_without_native_block(arguments, capsys):
    """参数错误把 argparse 的 2 转为 1，避免被宿主误解为原生拒绝。"""
    stdout = io.StringIO()
    streams = HookStreams(io.StringIO("{}"), stdout, io.StringIO())
    assert (
        run_hook("token-io-decoupling-workflow", arguments, streams=streams, checker=checker()) == 1
    )
    assert stdout.getvalue() == ""
    assert capsys.readouterr().err


def test_hook_help_returns_zero_without_running_a_check(capsys):
    """查看帮助应成功退出，且不能执行事件检查或输出 Hook JSON。"""
    stdout = io.StringIO()
    streams = HookStreams(io.StringIO("{}"), stdout, io.StringIO())
    assert (
        run_hook("token-io-decoupling-workflow", ["--help"], streams=streams, checker=checker())
        == 0
    )
    assert "usage:" in capsys.readouterr().out
    assert stdout.getvalue() == ""
