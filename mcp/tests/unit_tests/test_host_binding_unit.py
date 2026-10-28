from __future__ import annotations

import os
import socket
import threading
from typing import Any, cast

import pytest
from pydantic import ValidationError
from token_io_decoupling_core.binding import BindingError
from token_io_decoupling_core.host_binding import (
    MAX_FRAME,
    HostChannelBindingProvider,
    _Request,
    _validate_json,
)


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


def test_unconnected_socket_descriptor_is_rejected_and_closed() -> None:
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    fd = sock.detach()
    with pytest.raises(BindingError, match="must be connected"):
        HostChannelBindingProvider.from_fd(fd)
    assert sock.fileno() == -1
    with pytest.raises(OSError):
        os.fstat(fd)


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
