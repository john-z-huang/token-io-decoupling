from __future__ import annotations

import json
import os
import socket
import threading
import time
from typing import Any, cast

import pytest
from pydantic import ValidationError
from token_io_decoupling_core.binding import BindingError
from token_io_decoupling_core.host_binding import (
    MAX_FRAME,
    WIRE_PROTOCOL,
    HostChannelBindingProvider,
    _Request,
    _validate_json,
    serve_host_binding_channel,
)
from token_io_decoupling_core.state_models import (
    BindingIdentity,
    HostCapability,
    HostGuard,
    SessionRole,
    VerifiedChildBinding,
)


class _SyntheticHostProvider:
    """Test-only provider; it does not attest a real runtime or host session."""

    def __init__(self, role: SessionRole = SessionRole.PARENT) -> None:
        self.identity = BindingIdentity(
            project_id="synthetic-project",
            root_session_id="synthetic-root",
            current_session_id=(
                "synthetic-root" if role is SessionRole.PARENT else "synthetic-worker"
            ),
            role=role,
            capabilities=frozenset(HostCapability),
            guards=frozenset(HostGuard),
            parent_session_id="synthetic-root" if role is SessionRole.WORKER else None,
        )
        self.child = VerifiedChildBinding(
            project_id=self.identity.project_id,
            root_session_id=self.identity.root_session_id,
            parent_session_id=self.identity.root_session_id,
            child_session_id="synthetic-child",
            capabilities=frozenset(HostCapability),
            guards=frozenset(HostGuard),
        )

    def current_binding(self) -> BindingIdentity:
        return self.identity

    def verify_child_binding(
        self, parent: BindingIdentity, child_session_id: str
    ) -> VerifiedChildBinding:
        if parent != self.identity or child_session_id != self.child.child_session_id:
            raise BindingError("child denied")
        return self.child


def _channel(monkeypatch: pytest.MonkeyPatch, provider: _SyntheticHostProvider):
    client, host = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
    monkeypatch.setattr("token_io_decoupling_core.host_binding._peer_uid", lambda _sock: 0)
    thread = threading.Thread(target=serve_host_binding_channel, args=(host, provider), daemon=True)
    thread.start()
    return HostChannelBindingProvider(client), thread


def test_typed_channel_handshake_and_canonical_child_check(monkeypatch: pytest.MonkeyPatch) -> None:
    provider, thread = _channel(monkeypatch, _SyntheticHostProvider())
    try:
        assert provider.current_binding().current_session_id == "synthetic-root"
        child = provider.verify_child_binding(provider.current_binding(), "synthetic-child")
        assert child.parent_session_id == "synthetic-root"
        with pytest.raises(BindingError):
            provider.verify_child_binding(provider.current_binding(), "forged-child")
    finally:
        provider.close()
        thread.join(timeout=1)


def test_unverifiable_child_does_not_poison_valid_parent_channel(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider, thread = _channel(monkeypatch, _SyntheticHostProvider())
    try:
        with pytest.raises(BindingError, match="could not verify"):
            provider.verify_child_binding(provider.current_binding(), "unknown-child")
        assert provider.current_binding().role is SessionRole.PARENT
    finally:
        provider.close()
        thread.join(timeout=1)


def test_healthy_channel_survives_idle_gap(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("token_io_decoupling_core.host_binding.CHANNEL_TIMEOUT", 0.05)
    provider, thread = _channel(monkeypatch, _SyntheticHostProvider())
    try:
        time.sleep(0.12)
        assert provider.current_binding().role is SessionRole.PARENT
    finally:
        provider.close()
        thread.join(timeout=1)


def test_worker_cannot_verify_child(monkeypatch: pytest.MonkeyPatch) -> None:
    provider, thread = _channel(monkeypatch, _SyntheticHostProvider(SessionRole.WORKER))
    try:
        with pytest.raises(BindingError):
            provider.verify_child_binding(provider.current_binding(), "synthetic-child")
    finally:
        provider.close()
        thread.join(timeout=1)


def test_channel_rejects_real_same_uid_peer() -> None:
    if os.geteuid() == 0:
        cast(Any, pytest.skip)(
            "requires an unprivileged test process to exercise same-UID rejection"
        )
    client, host = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        with pytest.raises(BindingError, match="peer is not UID 0"):
            HostChannelBindingProvider(client)
    finally:
        host.close()


def test_root_client_is_rejected_before_handshake(monkeypatch: pytest.MonkeyPatch) -> None:
    client, _host = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
    monkeypatch.setattr("token_io_decoupling_core.host_binding.os.geteuid", lambda: 0)
    monkeypatch.setattr("token_io_decoupling_core.host_binding._peer_uid", lambda _sock: 0)
    with pytest.raises(BindingError, match="must not run as UID 0"):
        HostChannelBindingProvider(client)


def test_unconnected_socket_descriptor_is_rejected_and_closed() -> None:
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    fd = sock.detach()
    with pytest.raises(BindingError, match="must be connected"):
        HostChannelBindingProvider.from_fd(fd)
    assert sock.fileno() == -1
    with pytest.raises(OSError):
        os.fstat(fd)


def test_unsupported_peer_authentication_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    from token_io_decoupling_core.host_binding import _peer_uid

    client, host = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
    monkeypatch.setattr("token_io_decoupling_core.host_binding.sys.platform", "unknown-platform")
    try:
        with pytest.raises(BindingError, match="unsupported"):
            _peer_uid(client)
    finally:
        client.close()
        host.close()


def test_identity_change_poisons_channel(monkeypatch: pytest.MonkeyPatch) -> None:
    host_provider = _SyntheticHostProvider()
    provider, thread = _channel(monkeypatch, host_provider)
    try:
        host_provider.identity = host_provider.identity.model_copy(
            update={"current_session_id": "other-session"}
        )
        with pytest.raises(BindingError, match="identity changed"):
            provider.current_binding()
        with pytest.raises(BindingError, match="unavailable"):
            provider.current_binding()
    finally:
        provider.close()
        thread.join(timeout=1)


def test_capability_and_guard_changes_are_refreshed_from_host(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    host_provider = _SyntheticHostProvider()
    provider, thread = _channel(monkeypatch, host_provider)
    try:
        reduced = frozenset({HostCapability.WORKFLOW_READ})
        host_provider.identity = host_provider.identity.model_copy(
            update={"capabilities": reduced, "guards": frozenset({HostGuard.IDENTITY_BOUND})}
        )
        current = provider.current_binding()
        assert current.capabilities == reduced
        assert current.guards == frozenset({HostGuard.IDENTITY_BOUND})
        host_provider.identity = host_provider.identity.model_copy(
            update={"capabilities": frozenset(HostCapability), "guards": frozenset(HostGuard)}
        )
        assert provider.current_binding().capabilities == frozenset(HostCapability)
    finally:
        provider.close()
        thread.join(timeout=1)


def test_wire_schema_forbids_extra_fields_and_requires_valid_operation() -> None:
    with pytest.raises(ValidationError):
        _Request.model_validate_json(
            '{"protocol":"token-io-host/1","request_id":1,"operation":"current_binding",'
            '"child_session_id":null,'
            '"session_id":"untrusted"}'
        )
    with pytest.raises(ValidationError):
        _Request.model_validate_json('{"request_id":1,"operation":"current_binding"}')
    with pytest.raises(ValidationError):
        _Request.model_validate_json(
            '{"protocol":"token-io-host/2","request_id":1,"operation":"current_binding"}'
        )
    with pytest.raises(ValidationError):
        _Request.model_validate_json(
            '{"protocol":"token-io-host/1","request_id":1,"operation":"execute_sql"}'
        )
    with pytest.raises((ValidationError, ValueError)):
        _validate_json(
            _Request,
            b'{"protocol":"token-io-host/1","protocol":"token-io-host/1",'
            b'"request_id":1,"operation":"current_binding"}',
        )


def test_oversize_frame_is_rejected() -> None:
    left, right = socket.socketpair()
    try:
        sender = threading.Thread(target=right.sendall, args=(b"x" * (MAX_FRAME + 1) + b"\n",))
        sender.start()
        from token_io_decoupling_core.host_binding import _recv_frame

        with pytest.raises(BindingError, match="exceeds limit"):
            _recv_frame(left)
        sender.join(timeout=1)
    finally:
        left.close()
        right.close()


def test_out_of_order_response_permanently_poisons_channel(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, host = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
    monkeypatch.setattr("token_io_decoupling_core.host_binding._peer_uid", lambda _sock: 0)
    identity = _SyntheticHostProvider().identity

    def respond() -> None:
        from token_io_decoupling_core.host_binding import _recv_frame, _send_frame

        first_frame = _recv_frame(host)
        assert first_frame is not None
        first = json.loads(first_frame)
        _send_frame(
            host,
            json.dumps(
                {
                    "protocol": WIRE_PROTOCOL,
                    "request_id": first["request_id"],
                    "operation": "current_binding",
                    "ok": True,
                    "result": identity.model_dump(mode="json"),
                }
            ).encode(),
        )
        second_frame = _recv_frame(host)
        assert second_frame is not None
        second = json.loads(second_frame)
        _send_frame(
            host,
            json.dumps(
                {
                    "protocol": WIRE_PROTOCOL,
                    "request_id": second["request_id"] + 1,
                    "operation": "current_binding",
                    "ok": True,
                    "result": identity.model_dump(mode="json"),
                }
            ).encode(),
        )

    thread = threading.Thread(target=respond, daemon=True)
    thread.start()
    provider = HostChannelBindingProvider(client)
    try:
        with pytest.raises(BindingError, match="failed closed"):
            provider.current_binding()
        with pytest.raises(BindingError, match="unavailable"):
            provider.current_binding()
    finally:
        provider.close()
        host.close()
        thread.join(timeout=1)


@pytest.mark.parametrize(
    "malformation",
    ["operation", "version", "error_and_result", "success_with_error", "failure_without_error"],
)
def test_malformed_response_permanently_poisons_channel(
    monkeypatch: pytest.MonkeyPatch, malformation: str
) -> None:
    from token_io_decoupling_core.host_binding import _recv_frame, _send_frame

    client, host = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
    monkeypatch.setattr("token_io_decoupling_core.host_binding._peer_uid", lambda _sock: 0)
    identity = _SyntheticHostProvider().identity

    def respond() -> None:
        initial_frame = _recv_frame(host)
        assert initial_frame is not None
        initial = _Request.model_validate_json(initial_frame)
        _send_frame(
            host,
            json.dumps(
                {
                    "protocol": WIRE_PROTOCOL,
                    "request_id": initial.request_id,
                    "operation": initial.operation,
                    "ok": True,
                    "result": identity.model_dump(mode="json"),
                }
            ).encode(),
        )
        next_frame = _recv_frame(host)
        assert next_frame is not None
        request = _Request.model_validate_json(next_frame)
        response: dict[str, object] = {
            "protocol": WIRE_PROTOCOL,
            "request_id": request.request_id,
            "operation": request.operation,
            "ok": True,
            "result": identity.model_dump(mode="json"),
        }
        if malformation == "operation":
            response["operation"] = "verify_child_binding"
        elif malformation == "version":
            response["protocol"] = "token-io-host/2"
        elif malformation == "error_and_result":
            response.update({"ok": False, "error": "denied"})
        elif malformation == "success_with_error":
            response["error"] = "denied"
        else:
            response.update({"ok": False, "result": None})
        _send_frame(host, json.dumps(response).encode())

    thread = threading.Thread(target=respond, daemon=True)
    thread.start()
    provider = HostChannelBindingProvider(client)
    try:
        with pytest.raises(BindingError):
            provider.current_binding()
        with pytest.raises(BindingError, match="unavailable"):
            provider.current_binding()
    finally:
        provider.close()
        host.close()
        thread.join(timeout=1)


def test_slow_trickle_cannot_extend_whole_rpc_deadline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from token_io_decoupling_core.host_binding import _recv_frame, _send_frame

    monkeypatch.setattr("token_io_decoupling_core.host_binding.CHANNEL_TIMEOUT", 0.2)
    client, host = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
    monkeypatch.setattr("token_io_decoupling_core.host_binding._peer_uid", lambda _sock: 0)
    identity = _SyntheticHostProvider().identity

    def respond() -> None:
        initial_frame = _recv_frame(host)
        assert initial_frame is not None
        initial = _Request.model_validate_json(initial_frame)
        handshake = {
            "protocol": WIRE_PROTOCOL,
            "request_id": initial.request_id,
            "operation": initial.operation,
            "ok": True,
            "result": identity.model_dump(mode="json"),
        }
        _send_frame(host, json.dumps(handshake).encode())
        request_frame = _recv_frame(host)
        assert request_frame is not None
        request = _Request.model_validate_json(request_frame)
        response = {
            "protocol": WIRE_PROTOCOL,
            "request_id": request.request_id,
            "operation": request.operation,
            "ok": True,
            "result": identity.model_dump(mode="json"),
        }
        wire = json.dumps(response).encode() + b"\n"
        for byte in wire:
            try:
                host.sendall(bytes([byte]))
            except OSError:
                return
            time.sleep(0.03)

    thread = threading.Thread(target=respond, daemon=True)
    thread.start()
    provider = HostChannelBindingProvider(client)
    try:
        started = time.monotonic()
        with pytest.raises(BindingError):
            provider.current_binding()
        assert time.monotonic() - started < 1.5
        with pytest.raises(BindingError, match="unavailable"):
            provider.current_binding()
    finally:
        provider.close()
        host.close()
        thread.join(timeout=1)


@pytest.mark.parametrize("failure", ["eof", "oversize", "timeout"])
def test_transport_failure_poisons_channel(monkeypatch: pytest.MonkeyPatch, failure: str) -> None:
    from token_io_decoupling_core.host_binding import _recv_frame, _send_frame

    if failure == "timeout":
        monkeypatch.setattr("token_io_decoupling_core.host_binding.CHANNEL_TIMEOUT", 0.05)
    client, host = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
    monkeypatch.setattr("token_io_decoupling_core.host_binding._peer_uid", lambda _sock: 0)
    identity = _SyntheticHostProvider().identity

    def respond() -> None:
        first_frame = _recv_frame(host)
        assert first_frame is not None
        first = _Request.model_validate_json(first_frame)
        _send_frame(
            host,
            json.dumps(
                {
                    "protocol": WIRE_PROTOCOL,
                    "request_id": first.request_id,
                    "operation": first.operation,
                    "ok": True,
                    "result": identity.model_dump(mode="json"),
                }
            ).encode(),
        )
        if failure == "eof":
            host.close()
        elif failure == "oversize":
            sender = threading.Thread(target=host.sendall, args=(b"x" * (MAX_FRAME + 1) + b"\n",))
            sender.start()
            sender.join(timeout=2)
        else:
            host.recv(1)
            time.sleep(0.12)
            try:
                host.sendall(b"late\n")
            except OSError:
                pass

    thread = threading.Thread(target=respond, daemon=True)
    thread.start()
    provider = HostChannelBindingProvider(client)
    try:
        with pytest.raises(BindingError):
            provider.current_binding()
        with pytest.raises(BindingError, match="unavailable"):
            provider.current_binding()
    finally:
        provider.close()
        host.close()
        thread.join(timeout=1)
