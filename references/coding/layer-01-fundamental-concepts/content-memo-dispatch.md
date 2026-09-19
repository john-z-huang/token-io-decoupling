# Worker Content Memo Dispatch

This module defines the parent-controlled `write_content_memo` dispatch switch for a Worker's file-backed execution memo. It does not define memo content, memo lifecycle, context transport, or child lifecycle.

## Dispatch switch

The parent sets:

```text
write_content_memo: true
```

`true` is the default, including when the field is omitted. It enables the file-backed memo for the dispatch. `false` suppresses only the file-backed memo and is appropriate only when memo cost clearly exceeds likely reuse, recovery, or handoff value.

## Parent authority

The Worker cannot change or reinterpret the switch. Only the parent may choose a value for a later slice. This authority controls memo file materialization only; it does not grant any other scope or capability.
