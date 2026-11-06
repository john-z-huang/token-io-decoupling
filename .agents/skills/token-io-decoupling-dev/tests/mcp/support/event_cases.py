"""构造独立的事件事实与受控模型响应，避免测试访问真实 API。"""

from __future__ import annotations

from types import SimpleNamespace

from token_io_decoupling_workflow.decisions import DECISIONS_MODEL, DecisionsRuntimeConfig
from token_io_decoupling_workflow.events.advice import EventAdvisor
from token_io_decoupling_workflow.events.checks import WorkflowEventChecker
from token_io_decoupling_workflow.events.models import EventCheckRequest
from token_io_decoupling_workflow.rules import RuleLoader

EVENT_REQUIREMENTS = {
    "task_received": (["task", "constraints", "session_context"], ["request_source"]),
    "boundary_requested": (
        ["objective", "proposed_action", "scope", "session_context"],
        ["authorization_scope"],
    ),
    "action_observed": (["action", "result", "scope"], ["operation_result"]),
    "progress_reported": (["objective", "progress", "boundary"], ["progress_signal"]),
    "completion_requested": (
        ["objective", "acceptance", "results"],
        ["verification_result", "final_state"],
    ),
    "session_resumed": (
        ["retained_context", "pending_work", "effect_status"],
        ["context_source"],
    ),
}


def request_data(event="task_received", **changes):
    """构造具有当前事件所需事实和证据的请求数据，允许用例显式覆盖单项前提。"""
    facts, evidence = EVENT_REQUIREMENTS[event]
    request = {
        "event": event,
        "context_summary": "当前 Agent 上下文；输入事实尚未认证。",
        "facts": {
            name: {"value": f"current {name}", "source": "conversation:user-request"}
            for name in facts
        },
        "evidence_refs": [
            {"kind": kind, "reference": f"conversation:evidence:{kind}"} for kind in evidence
        ],
    }
    request.update(changes)
    return request


def request(event="task_received", **changes):
    """通过真实 Pydantic 模型校验场景请求，不让假客户端绕开输入边界。"""
    return EventCheckRequest.model_validate(request_data(event, **changes))


def response(outcome="continue", **changes):
    """生成合法且有固定用量的模型选择，供成功和损坏响应场景共享。"""
    fields = {
        "answers": [SimpleNamespace(type="choice", name="workflow_event_outcome", choice=outcome)],
        "model": DECISIONS_MODEL,
        "status": "completed",
        "error": None,
        "incomplete_details": None,
        "usage": SimpleNamespace(total_tokens=17),
    }
    fields.update(changes)
    return SimpleNamespace(**fields)


class FakeClient:
    """记录模型请求、可控响应及关闭动作，不承担规则加载或跨调用状态职责。"""

    def __init__(self, result=None, error=None, callback=None):
        """保存默认响应及可选调用回调，让测试控制模型返回与规则竞争时点。"""
        self.result = result if result is not None else response()
        self.error = error
        self.callback = callback
        self.calls = []
        self.closed = False
        self.decisions = self

    def create(self, **kwargs):
        """先记录真实请求，再执行故障或规则变化回调，最后交付指定响应。"""
        self.calls.append(kwargs)
        if self.callback:
            self.callback()
        if self.error:
            raise self.error
        return self.result

    def close(self):
        """记录客户端已关闭，供请求与异常生命周期断言使用。"""
        self.closed = True


def checker(*, rules=None, enabled=False, outbound=False, client=None, factory=None):
    """组合真实 RuleLoader、静态检查与可控模型边界，宿主和逐调用许可仍由生产代码判断。"""
    rules = rules if rules is not None else RuleLoader()
    if factory is None and client is not None:

        def factory(_key, _url):
            """只在生产代码允许构造客户端时返回替身，便于证明被拒请求没有触达模型。"""
            return client

    advisor = EventAdvisor(
        rules,
        DecisionsRuntimeConfig(enabled=enabled, outbound_data_permitted=outbound),
        client_factory=factory,
    )
    return WorkflowEventChecker(rules, advisor)
