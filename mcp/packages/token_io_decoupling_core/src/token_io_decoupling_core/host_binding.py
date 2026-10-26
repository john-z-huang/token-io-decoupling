"""Authenticated, bounded RPC bridge to a privileged trusted embedding host.

The bridge authenticates only the peer process. Identity and guard evidence still
come exclusively from the provider attached out of band by that host.
"""

from __future__ import annotations

import ctypes
import json
import os
import socket
import struct
import sys
import threading
import time
from typing import Literal, TypeVar

from pydantic import Field, StrictInt, model_validator

from token_io_decoupling_core.binding import BindingError, BindingProvider
from token_io_decoupling_core.models import StrictModel
from token_io_decoupling_core.state_models import (
    BindingIdentity,
    HostCapability,
    HostGuard,
    SessionRole,
    VerifiedChildBinding,
)

MAX_FRAME = 64 * 1024
CHANNEL_TIMEOUT = 5.0
WIRE_PROTOCOL = "token-io-host/1"
_SAFE_ERRORS = {"unavailable", "denied", "invalid_request", "internal_error", "child_unverified"}
_ModelT = TypeVar("_ModelT", bound=StrictModel)


class _Request(StrictModel):
    protocol: Literal["token-io-host/1"]
    request_id: StrictInt = Field(ge=1)
    operation: Literal["current_binding", "verify_child_binding"]
    child_session_id: str | None = None


class _Response(StrictModel):
    protocol: Literal["token-io-host/1"]
    request_id: StrictInt = Field(ge=1)
    operation: Literal["current_binding", "verify_child_binding"]
    ok: bool
    result: dict[str, object] | None = None
    error: (
        Literal["unavailable", "denied", "invalid_request", "internal_error", "child_unverified"]
        | None
    ) = None

    @model_validator(mode="after")
    def validate_result_shape(self) -> _Response:
        if self.ok:
            if self.result is None or self.error is not None:
                raise ValueError("successful response requires a result and no error")
        elif self.result is not None or self.error is None:
            raise ValueError("failed response requires an error and no result")
        return self


def _peer_uid(sock: socket.socket) -> int:
    if sys.platform.startswith("linux"):
        option = getattr(socket, "SO_PEERCRED", None)
        if option is None:
            raise BindingError("kernel peer authentication is unsupported on this platform")
        try:
            raw = sock.getsockopt(socket.SOL_SOCKET, option, struct.calcsize("3i"))
        except OSError:
            raise BindingError("kernel peer authentication failed") from None
        _pid, uid, _gid = struct.unpack("3i", raw)
        return uid
    if sys.platform == "darwin":
        try:
            libc = ctypes.CDLL(None, use_errno=True)
            getpeereid = getattr(libc, "getpeereid", None)
            if getpeereid is None:
                raise BindingError("kernel peer authentication is unsupported on this platform")
            uid = ctypes.c_uint32()
            gid = ctypes.c_uint32()
            getpeereid.argtypes = [
                ctypes.c_int,
                ctypes.POINTER(ctypes.c_uint32),
                ctypes.POINTER(ctypes.c_uint32),
            ]
            getpeereid.restype = ctypes.c_int
            if getpeereid(sock.fileno(), ctypes.byref(uid), ctypes.byref(gid)) != 0:
                raise BindingError("kernel peer authentication failed")
            return uid.value
        except OSError:
            raise BindingError("kernel peer authentication failed") from None
    raise BindingError("kernel peer authentication is unsupported on this platform")


def _recv_frame(
    sock: socket.socket,
    *,
    idle_ok: bool = False,
    deadline: float | None = None,
) -> bytes | None:
    data = bytearray()
    while len(data) < MAX_FRAME:
        if deadline is not None:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise BindingError("host frame timed out")
            sock.settimeout(remaining)
        try:
            byte = sock.recv(1)
        except TimeoutError:
            if idle_ok and not data:
                return None
            raise BindingError("host frame timed out") from None
        if not byte:
            raise BindingError("host channel closed")
        if not data:
            if deadline is None:
                deadline = time.monotonic() + CHANNEL_TIMEOUT
        if byte == b"\n":
            if not data:
                raise BindingError("empty host response")
            return bytes(data)
        data.extend(byte)
        if deadline is None:
            raise BindingError("host frame deadline unavailable")
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise BindingError("host frame timed out")
        sock.settimeout(remaining)
    raise BindingError("host frame exceeds limit")


def _send_frame(sock: socket.socket, payload: bytes, *, deadline: float | None = None) -> None:
    if not payload or len(payload) + 1 > MAX_FRAME:
        raise BindingError("host frame exceeds limit")
    if deadline is not None:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise BindingError("host operation timed out")
        sock.settimeout(remaining)
    sock.sendall(payload + b"\n")


def _validate_socket(sock: socket.socket) -> None:
    if (
        sock.family != socket.AF_UNIX
        or sock.getsockopt(socket.SOL_SOCKET, socket.SO_TYPE) != socket.SOCK_STREAM
    ):
        raise BindingError("host descriptor must be a connected AF_UNIX stream")
    try:
        sock.getpeername()
    except OSError as exc:
        raise BindingError("host descriptor must be connected") from exc


def _validate_json(model: type[_ModelT], data: bytes) -> _ModelT:
    def unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result

    def reject_constant(_value: str) -> None:
        raise ValueError("nonfinite JSON number")

    json.loads(data, object_pairs_hook=unique_object, parse_constant=reject_constant)
    return model.model_validate_json(data)


class HostChannelBindingProvider:
    """Client binding provider for an inherited socket authenticated to UID 0."""

    transport = "authenticated_inherited_unix_socket"

    def __init__(self, sock: socket.socket) -> None:
        self._socket = sock
        try:
            _validate_socket(sock)
            self._socket.set_inheritable(False)
            self._socket.settimeout(CHANNEL_TIMEOUT)
        except Exception:
            sock.close()
            raise
        self._lock = threading.Lock()
        self._request_id = 0
        self._poisoned = False
        self._closed = False
        try:
            effective_uid = getattr(os, "geteuid", None)
            if effective_uid is None:
                raise BindingError("unprivileged client identity is unavailable")
            if effective_uid() == 0:
                raise BindingError("channel client must not run as UID 0")
            if _peer_uid(sock) != 0:
                raise BindingError("host channel peer is not UID 0")
            self._identity = self._rpc("current_binding", None, BindingIdentity)
        except Exception:
            self.close()
            raise

    @classmethod
    def from_fd(cls, fd: int) -> HostChannelBindingProvider:
        if fd < 3:
            raise BindingError("host descriptor must be at least 3")
        try:
            sock = socket.socket(fileno=fd)
        except OSError as exc:
            raise BindingError("host descriptor is not an available socket") from exc
        return cls(sock)

    def current_binding(self) -> BindingIdentity:
        current = self._rpc("current_binding", None, BindingIdentity)
        if self._stable_identity(current) != self._stable_identity(self._identity):
            self._poison("host identity changed during session")
        return current

    def verify_child_binding(
        self, parent: BindingIdentity, child_session_id: str
    ) -> VerifiedChildBinding:
        current = self.current_binding()
        if current.role.value != "parent":
            raise BindingError("only a parent binding can verify a child")
        if self._stable_identity(parent) != self._stable_identity(current):
            raise BindingError("requested parent does not match canonical host identity")
        child = self._rpc("verify_child_binding", child_session_id, VerifiedChildBinding)
        if (
            child.project_id != current.project_id
            or child.root_session_id != current.root_session_id
            or child.parent_session_id != current.current_session_id
            or child.child_session_id != child_session_id
        ):
            self._poison("host returned a mismatched child identity")
        return child

    @staticmethod
    def _stable_identity(value: BindingIdentity) -> tuple[object, ...]:
        return (
            value.project_id,
            value.root_session_id,
            value.current_session_id,
            value.role,
            value.parent_session_id,
        )

    def _poison(self, message: str) -> None:
        self._poisoned = True
        self.close()
        raise BindingError(message)

    def _rpc(
        self,
        operation: Literal["current_binding", "verify_child_binding"],
        child_id: str | None,
        result_type: type[_ModelT],
    ) -> _ModelT:
        with self._lock:
            if self._poisoned or self._closed:
                raise BindingError("host channel is unavailable")
            self._request_id += 1
            request_id = self._request_id
            deadline = time.monotonic() + CHANNEL_TIMEOUT
            request = _Request(
                protocol=WIRE_PROTOCOL,
                request_id=request_id,
                operation=operation,
                child_session_id=child_id,
            )
            nonfatal_denial = False
            try:
                _send_frame(self._socket, request.model_dump_json().encode(), deadline=deadline)
                frame = _recv_frame(self._socket, deadline=deadline)
                if frame is None or time.monotonic() > deadline:
                    raise BindingError("host operation timed out")
                response = _validate_json(_Response, frame)
                if response.request_id != request_id or response.operation != operation:
                    raise ValueError("out-of-order host response")
                if not response.ok:
                    if response.error not in _SAFE_ERRORS:
                        raise ValueError("invalid host error")
                    if operation == "verify_child_binding" and response.error == "child_unverified":
                        nonfatal_denial = True
                        raise BindingError("trusted host could not verify the requested child")
                    self._poisoned = True
                    self.close()
                    raise BindingError("trusted host denied the binding request")
                if response.result is None:
                    raise ValueError("malformed host response")
                return result_type.model_validate_json(json.dumps(response.result))
            except BindingError:
                if not nonfatal_denial and not self._poisoned:
                    self._poisoned = True
                    self.close()
                raise
            except Exception as exc:
                self._poisoned = True
                self.close()
                raise BindingError("host channel failed closed") from exc

    def close(self) -> None:
        if not self._closed:
            self._closed = True
            self._socket.close()


def serve_host_binding_channel(sock: socket.socket, provider: BindingProvider) -> None:
    """Serve one channel; provider is the trusted host's out-of-band session binding."""
    try:
        _validate_socket(sock)
        sock.set_inheritable(False)
        sock.settimeout(CHANNEL_TIMEOUT)
        last_request_id = 0
        while True:
            request: _Request | None = None
            try:
                sock.settimeout(CHANNEL_TIMEOUT)
                frame = _recv_frame(sock, idle_ok=True)
                if frame is None:
                    continue
                deadline = time.monotonic() + CHANNEL_TIMEOUT
                request = _validate_json(_Request, frame)
                if request.request_id != last_request_id + 1:
                    return
                last_request_id = request.request_id
                if request.operation == "current_binding":
                    if request.child_session_id is not None:
                        raise ValueError("unexpected child field")
                    result = provider.current_binding()
                else:
                    if not request.child_session_id:
                        raise ValueError("missing child field")
                    parent = provider.current_binding()
                    required_guards = {
                        HostGuard.IDENTITY_BOUND,
                        HostGuard.SESSION_BOUND,
                        HostGuard.PATH_BOUNDARY,
                        HostGuard.PARENT_CHILD_RELATION,
                    }
                    if (
                        parent.role is not SessionRole.PARENT
                        or HostCapability.CHILD_IDENTITY_CHECK not in parent.capabilities
                        or not required_guards <= parent.guards
                    ):
                        raise BindingError("parent child-verification authority is unavailable")
                    try:
                        result = provider.verify_child_binding(parent, request.child_session_id)
                    except BindingError:
                        response = _Response(
                            protocol=WIRE_PROTOCOL,
                            request_id=request.request_id,
                            operation=request.operation,
                            ok=False,
                            error="child_unverified",
                        )
                    else:
                        response = _Response(
                            protocol=WIRE_PROTOCOL,
                            request_id=request.request_id,
                            operation=request.operation,
                            ok=True,
                            result=result.model_dump(mode="json"),
                        )
                    # This response is final for this operation; continue with the next request.
                    try:
                        _send_frame(sock, response.model_dump_json().encode(), deadline=deadline)
                    except Exception:
                        return
                    continue
                response = _Response(
                    protocol=WIRE_PROTOCOL,
                    request_id=request.request_id,
                    operation=request.operation,
                    ok=True,
                    result=result.model_dump(mode="json"),
                )
            except BindingError:
                if request is None:
                    return
                response = _Response(
                    protocol=WIRE_PROTOCOL,
                    request_id=request.request_id,
                    operation=request.operation,
                    ok=False,
                    error="denied",
                )
            except (ValueError, TypeError):
                if request is None:
                    return
                response = _Response(
                    protocol=WIRE_PROTOCOL,
                    request_id=request.request_id,
                    operation=request.operation,
                    ok=False,
                    error="invalid_request",
                )
            except Exception:
                if request is None:
                    return
                response = _Response(
                    protocol=WIRE_PROTOCOL,
                    request_id=request.request_id,
                    operation=request.operation,
                    ok=False,
                    error="internal_error",
                )
            try:
                _send_frame(sock, response.model_dump_json().encode(), deadline=deadline)
            except Exception:
                return
    except (BindingError, OSError):
        return
    finally:
        sock.close()
