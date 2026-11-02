"""Safe API-call and usage telemetry for the bounded optimization benchmark."""

from __future__ import annotations

import os
import threading
import time
from collections import Counter
from collections.abc import Callable, Iterable, Mapping
from typing import Any, cast

FIXED_MODEL = "gpt-6-luna"
_USAGE_FIELDS = ("input_tokens", "output_tokens", "total_tokens")


class BenchmarkCredentialError(RuntimeError):
    """Required process credentials are unavailable."""

    def __init__(self, variable: str) -> None:
        super().__init__(f"{variable}_must_be_set_to_a_nonblank_value")
        self.variable = variable


class BenchmarkHTTPAttemptLimitExceeded(RuntimeError):
    """The benchmark's outbound HTTP attempt ceiling has been reached."""

    def __init__(self) -> None:
        super().__init__("benchmark_http_attempt_limit_exceeded")


def _field(value: object, name: str) -> object:
    if isinstance(value, Mapping):
        return value.get(name)
    try:
        return getattr(value, name)
    except (AttributeError, TypeError):
        return None


def _safe_text(value: object) -> str | None:
    if not isinstance(value, str) or not value or len(value) > 128:
        return None
    if any(ord(character) < 32 for character in value):
        return None
    return value


def _token_value(value: object) -> int | None:
    if type(value) is not int or value < 0:
        return None
    return value


def _usage_field(usage: object, field: str) -> int | None:
    names = {
        "input_tokens": ("input_tokens", "prompt_tokens"),
        "output_tokens": ("output_tokens", "completion_tokens"),
        "total_tokens": ("total_tokens",),
    }[field]
    for name in names:
        value = _token_value(_field(usage, name))
        if value is not None:
            return value
    return None


def _requested_effort(kwargs: Mapping[str, object]) -> str | None:
    reasoning = kwargs.get("reasoning")
    return _safe_text(_field(reasoning, "effort"))


def _reported_effort(response: object) -> str | None:
    return _safe_text(_field(_field(response, "reasoning"), "effort"))


def _build_openai_client(
    *,
    api_key: str,
    base_url: str,
    timeout: float,
    max_retries: int,
    request_hook: Callable[[object], None],
    transport: object | None,
) -> object:
    from openai import DefaultHttpx2Client, OpenAI

    http_client_options: dict[str, Any] = {
        "timeout": timeout,
        "event_hooks": {"request": [cast(Any, request_hook)]},
    }
    if transport is not None:
        http_client_options["transport"] = cast(Any, transport)
    http_client = DefaultHttpx2Client(**http_client_options)
    return OpenAI(
        api_key=api_key,
        base_url=base_url,
        timeout=timeout,
        max_retries=max_retries,
        http_client=http_client,
    )


class _NamespaceProxy:
    def __init__(
        self,
        recorder: Recorder,
        namespace: object,
        *,
        api: str,
        method_name: str,
        case_id: str,
        arm: str,
        component: str,
        timeout_seconds: float,
    ) -> None:
        self._recorder = recorder
        self._namespace = namespace
        self._api = api
        self._method_name = method_name
        self._case_id = case_id
        self._arm = arm
        self._component = component
        self._timeout_seconds = timeout_seconds

    def __getattr__(self, name: str) -> Any:
        target = getattr(self._namespace, name)
        if name != self._method_name or not callable(target):
            return target

        def call(*args: object, **kwargs: object) -> Any:
            return self._recorder._invoke(
                target,
                args,
                kwargs,
                api=self._api,
                case_id=self._case_id,
                arm=self._arm,
                component=self._component,
                timeout_seconds=self._timeout_seconds,
            )

        return call


class _ClientProxy:
    def __init__(
        self,
        recorder: Recorder,
        client: object,
        *,
        case_id: str,
        arm: str,
        component: str,
        timeout_seconds: float,
    ) -> None:
        self._recorder = recorder
        self._client = client
        self._case_id = case_id
        self._arm = arm
        self._component = component
        self._timeout_seconds = timeout_seconds

    def __getattr__(self, name: str) -> Any:
        if name == "responses":
            return _NamespaceProxy(
                self._recorder,
                getattr(self._client, name),
                api="responses",
                method_name="parse",
                case_id=self._case_id,
                arm=self._arm,
                component=self._component,
                timeout_seconds=self._timeout_seconds,
            )
        if name == "decisions":
            return _NamespaceProxy(
                self._recorder,
                getattr(self._client, name),
                api="decisions",
                method_name="create",
                case_id=self._case_id,
                arm=self._arm,
                component=self._component,
                timeout_seconds=self._timeout_seconds,
            )
        return getattr(self._client, name)

    def close(self) -> None:
        close = getattr(self._client, "close", None)
        if callable(close):
            close()

    def __enter__(self) -> _ClientProxy:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()


class Recorder:
    """Create explicit-credential OpenAI clients and retain only safe telemetry.

    Normal benchmark runs use an explicit process key and base URL, the SDK's
    real HTTP transport, and one retry policy: no retries. Tests replace the
    private builder or inject a mock transport to avoid network calls.
    """

    def __init__(
        self,
        max_http_attempts: int = 30,
        *,
        transport: object | None = None,
    ) -> None:
        if type(max_http_attempts) is not int or max_http_attempts < 1:
            raise ValueError("max_http_attempts_must_be_a_positive_integer")
        self.max_http_attempts = max_http_attempts
        self.http_attempts = 0
        self.calls: list[dict[str, object]] = []
        self._transport = transport
        self._lock = threading.Lock()
        self._local = threading.local()

    def _request_event(self, _request: object) -> None:
        with self._lock:
            if self.http_attempts >= self.max_http_attempts:
                raise BenchmarkHTTPAttemptLimitExceeded()
            self.http_attempts += 1
        attempt_counter = getattr(self._local, "attempt_counter", None)
        if isinstance(attempt_counter, list):
            attempt_counter[0] += 1

    def make_client(
        self,
        *,
        case_id: str,
        arm: str,
        component: str,
        timeout: float,
    ) -> _ClientProxy:
        for name, value in (
            ("case_id", case_id),
            ("arm", arm),
            ("component", component),
        ):
            if _safe_text(value) is None:
                raise ValueError(f"{name}_must_be_nonblank_bounded_text")
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)):
            raise ValueError("timeout_must_be_positive")
        if timeout <= 0:
            raise ValueError("timeout_must_be_positive")

        api_key = os.environ.get("OPENAI_API_KEY")
        if api_key is None or not api_key.strip():
            raise BenchmarkCredentialError("OPENAI_API_KEY")
        base_url = os.environ.get("OPENAI_BASE_URL")
        if base_url is None or not base_url.strip():
            raise BenchmarkCredentialError("OPENAI_BASE_URL")

        client = _build_openai_client(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            max_retries=0,
            request_hook=self._request_event,
            transport=self._transport,
        )
        return _ClientProxy(
            self,
            client,
            case_id=case_id,
            arm=arm,
            component=component,
            timeout_seconds=float(timeout),
        )

    def _invoke(
        self,
        method: Any,
        args: tuple[object, ...],
        kwargs: Mapping[str, object],
        *,
        api: str,
        case_id: str,
        arm: str,
        component: str,
        timeout_seconds: float,
    ) -> object:
        start = time.perf_counter()
        attempt_counter = [0]
        previous_counter = getattr(self._local, "attempt_counter", None)
        self._local.attempt_counter = attempt_counter
        try:
            response = method(*args, **dict(kwargs))
        except Exception as exc:
            self._append_call(
                self._call_record(
                    api=api,
                    case_id=case_id,
                    arm=arm,
                    component=component,
                    timeout_seconds=timeout_seconds,
                    args=args,
                    kwargs=kwargs,
                    response=None,
                    status="error",
                    error_type=type(exc).__name__,
                    duration_ms=(time.perf_counter() - start) * 1000,
                    http_attempts=attempt_counter[0],
                )
            )
            raise
        else:
            self._append_call(
                self._call_record(
                    api=api,
                    case_id=case_id,
                    arm=arm,
                    component=component,
                    timeout_seconds=timeout_seconds,
                    args=args,
                    kwargs=kwargs,
                    response=response,
                    status="success",
                    error_type=None,
                    duration_ms=(time.perf_counter() - start) * 1000,
                    http_attempts=attempt_counter[0],
                )
            )
            return response
        finally:
            if previous_counter is None:
                try:
                    del self._local.attempt_counter
                except AttributeError:
                    pass
            else:
                self._local.attempt_counter = previous_counter

    @staticmethod
    def _call_record(
        *,
        api: str,
        case_id: str,
        arm: str,
        component: str,
        timeout_seconds: float,
        args: tuple[object, ...],
        kwargs: Mapping[str, object],
        response: object | None,
        status: str,
        error_type: str | None,
        duration_ms: float,
        http_attempts: int,
    ) -> dict[str, object]:
        requested_model = _safe_text(kwargs.get("model"))
        usage_object = _field(response, "usage") if response is not None else None
        usage = {field: _usage_field(usage_object, field) for field in _USAGE_FIELDS}
        return {
            "case_id": case_id,
            "arm": arm,
            "component": component,
            "api": api,
            "operation": "parse" if api == "responses" else "create",
            "status": status,
            "error_type": error_type,
            "requested_model": requested_model,
            "reported_model": _safe_text(_field(response, "model"))
            if response is not None
            else None,
            "requested_effort": _requested_effort(kwargs),
            "reported_effort": _reported_effort(response) if response is not None else None,
            "duration_ms": round(max(0.0, duration_ms), 3),
            "timeout_seconds": timeout_seconds,
            "http_attempts": http_attempts,
            "usage": usage,
        }

    def _append_call(self, call: dict[str, object]) -> None:
        with self._lock:
            self.calls.append(call)


def aggregate_calls(calls: Iterable[Mapping[str, object]]) -> dict[str, object]:
    """Aggregate fully reported usage without converting unknown values to zero."""

    records = list(calls)
    for record in records:
        if not isinstance(record, Mapping):
            raise TypeError("calls_must_contain_mappings")

    totals: dict[str, int | None] = {}
    known_subtotals: dict[str, int | None] = {}
    field_coverage: dict[str, dict[str, int | float | None]] = {}
    for field in _USAGE_FIELDS:
        values: list[int] = []
        for record in records:
            usage = record.get("usage")
            value = _token_value(_field(usage, field))
            if value is not None:
                values.append(value)
        reported = len(values)
        field_coverage[field] = {
            "reported_calls": reported,
            "total_calls": len(records),
            "fraction": reported / len(records) if records else None,
        }
        known_subtotals[field] = sum(values) if values else None
        totals[field] = None

    complete_calls = 0
    for record in records:
        usage = record.get("usage")
        if all(_token_value(_field(usage, field)) is not None for field in _USAGE_FIELDS):
            complete_calls += 1
    if records and complete_calls == len(records):
        totals = known_subtotals.copy()

    component_counts = Counter(
        component
        for record in records
        if (component := _safe_text(record.get("component"))) is not None
    )
    operation_counts = Counter(
        operation
        for record in records
        if (operation := _safe_text(record.get("operation"))) is not None
    )
    elapsed_ms = sum(
        duration
        for record in records
        if (duration := record.get("duration_ms")) is not None
        and isinstance(duration, (int, float))
        and not isinstance(duration, bool)
        and duration >= 0
    )

    return {
        "api_calls": len(records),
        "api_calls_by_component": dict(sorted(component_counts.items())),
        "api_calls_by_operation": dict(sorted(operation_counts.items())),
        "elapsed_ms": round(elapsed_ms, 3),
        "usage": totals,
        "known_subtotal": known_subtotals,
        "usage_coverage": {
            "complete_calls": complete_calls,
            "total_calls": len(records),
            "complete_fraction": complete_calls / len(records) if records else None,
            "fields": field_coverage,
        },
    }
