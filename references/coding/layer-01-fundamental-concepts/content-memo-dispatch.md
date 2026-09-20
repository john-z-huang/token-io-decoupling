# Worker Content Memo Dispatch

[English](content-memo-dispatch.md) | [简体中文](content-memo-dispatch_zh_cn.md)

This module defines the parent-controlled `write_content_memo` dispatch switch for a Worker's file-backed execution memo. It does not define memo content, memo lifecycle, context transport, or child lifecycle.

## Dispatch switch

The parent sets:

```text
write_content_memo: true
```

`true` is the default, including when the field is omitted. It enables the file-backed memo for the dispatch. `false` suppresses only the file-backed memo and is appropriate only when memo cost clearly exceeds likely reuse, recovery, or handoff value.

Internal dispatch configuration may omit the field and use this `true` default. Before the parent serializes a released task bundle, it must write `write_content_memo: true` or `write_content_memo: false` explicitly. A Worker consumes only the explicit value in its released bundle; if the released bundle omits the field, the dispatch is incomplete and the Worker must not infer a default.

## Parent authority

The Worker cannot change or reinterpret the switch. Only the parent may choose a value for a later slice. This authority controls memo file materialization only; it does not grant any other scope or capability.

## Related concepts

- [Worker Content Memo](content-memo.md) — locate the memo content contract.
- [Worker Content Memo Lifecycle](content-memo-lifecycle.md) — locate memo lifecycle rules.
