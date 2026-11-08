"""受界限约束的单次 Hook 标准输入输出入口，不修改真实宿主配置。"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from typing import TextIO

from pydantic import ConfigDict, JsonValue, TypeAdapter, ValidationError

from token_io_decoupling_workflow.advisory.models import DecisionsRuntimeConfig
from token_io_decoupling_workflow.compiled_rules.loader import RuleLoader
from token_io_decoupling_workflow.events.advice import EventAdvisor
from token_io_decoupling_workflow.events.checks import WorkflowEventChecker
from token_io_decoupling_workflow.events.contracts import DEFAULT_EVENT_TEXT_BUDGET
from token_io_decoupling_workflow.events.models import (
    MAX_EVENT_REQUEST_BYTES,
    canonical_event_json,
)
from token_io_decoupling_workflow.events.native import (
    MAX_HOOK_OUTPUT_BYTES,
    NativeHookOptions,
    native_hook_response,
    normalize_native_event,
)

_JSON_OBJECT = TypeAdapter(dict[str, JsonValue], config=ConfigDict(allow_inf_nan=False))


@dataclass(frozen=True)
class HookStreams:
    """宿主进程的标准流；测试可显式替换，避免隐式全局 I/O。"""

    stdin: TextIO
    stdout: TextIO
    stderr: TextIO


def _parse_options(prog: str, argv: list[str]) -> NativeHookOptions:
    """只接受已支持模式与显式语义开关，将参数组合交给严格模型验证。"""
    parser = argparse.ArgumentParser(prog=prog, description="检查一次原生 Codex Hook 输入。")
    parser.add_argument("--mode", choices=("single-agent", "multi-agent"))
    parser.add_argument("--language", choices=("zh_cn",), default="zh_cn")
    parser.add_argument("--max-chars", type=int, default=DEFAULT_EVENT_TEXT_BUDGET)
    parser.add_argument("--semantic", action="store_true")
    parser.add_argument("--outbound-data-permitted", action="store_true")
    parser.add_argument("--block-once", action="store_true")
    try:
        return NativeHookOptions.model_validate(vars(parser.parse_args(argv)))
    except ValidationError:
        parser.error("invalid Hook options, text bound or explicit outbound permission")


def _read_payload(stream: TextIO) -> dict[str, JsonValue]:
    """按 UTF-8 字节限制原生输入，并再次拒绝递归 JSON 中的非有限数值。"""
    raw = stream.read(MAX_EVENT_REQUEST_BYTES + 1)
    if len(raw.encode("utf-8")) > MAX_EVENT_REQUEST_BYTES:
        raise ValueError("native hook input exceeds its supported bound")
    payload = _JSON_OBJECT.validate_json(raw)
    # JSON 数值配置不适用于所有递归 JsonValue 分支，序列化再次拒绝非标准值。
    canonical_event_json(payload)
    return payload


def _make_checker(options: NativeHookOptions) -> WorkflowEventChecker:
    """仅按本次命令选项装配静态检查和建议开关，不建立持久运行实例。"""
    rules = RuleLoader()
    config = DecisionsRuntimeConfig(
        enabled=options.semantic,
        outbound_data_permitted=options.semantic and options.outbound_data_permitted,
    )
    return WorkflowEventChecker(rules, EventAdvisor(rules, config))


def run_hook(
    prog: str,
    argv: list[str],
    *,
    streams: HookStreams | None = None,
    checker: WorkflowEventChecker | None = None,
) -> int:
    """处理一次有界 JSON；运行故障返回 1，避免被宿主误作 exit 2 拒绝。"""
    streams = streams if streams is not None else HookStreams(sys.stdin, sys.stdout, sys.stderr)
    try:
        options = _parse_options(prog, argv)
    except SystemExit as exc:
        # argparse 的 exit 2 会被原生宿主视为阻塞，配置错误统一转为普通故障。
        return 0 if exc.code == 0 else 1
    try:
        payload = _read_payload(streams.stdin)
        checker = checker if checker is not None else _make_checker(options)
        checked = checker.check(normalize_native_event(payload, options))
        response = native_hook_response(payload, checked, options)
        encoded = canonical_event_json(response)
        if len(encoded.encode("utf-8")) > MAX_HOOK_OUTPUT_BYTES:
            raise ValueError("native hook output exceeds its supported bound")
        streams.stdout.write(encoded + "\n")
    except Exception:
        # CLI 边界不向宿主回显外部 payload、路径、凭据或原始供应商异常。
        streams.stderr.write("workflow hook input or instructions could not be processed\n")
        return 1
    return 0
