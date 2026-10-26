"""Paging helpers for the state service."""

from __future__ import annotations

from token_io_decoupling_core.state_models import (
    RecoveryIndexCollection,
    RecoveryIndexCursor,
    RecoveryIndexPageInfo,
    RecoveryIndexPageRequest,
)

from .errors import StaleRecoveryCursorError


def _recovery_page_bounds(
    collection: str,
    current_revision: int,
    total_count: int,
    request: RecoveryIndexPageRequest | None,
    default_page_size: int,
) -> tuple[int, int]:
    if request is None or request.collection != collection:
        return 0, default_page_size
    if request.cursor is None:
        return 0, request.page_size or default_page_size
    if request.cursor.revision != current_revision:
        raise StaleRecoveryCursorError(
            f"recovery cursor Revision {request.cursor.revision} is stale; current Revision is "
            f"{current_revision}"
        )
    if request.cursor.offset > total_count:
        raise ValueError("recovery cursor offset exceeds the index total_count")
    return request.cursor.offset, request.cursor.page_size


def _recovery_page_info(
    collection: RecoveryIndexCollection,
    revision: int,
    offset: int,
    page_size: int,
    total: int,
    returned: int,
) -> RecoveryIndexPageInfo:
    next_offset = offset + returned
    next_cursor = (
        RecoveryIndexCursor(
            collection=collection,
            revision=revision,
            offset=next_offset,
            page_size=page_size,
        )
        if next_offset < total
        else None
    )
    return RecoveryIndexPageInfo(
        collection=collection,
        revision=revision,
        offset=offset,
        page_size=page_size,
        total_count=total,
        returned_count=returned,
        next_cursor=next_cursor,
    )
