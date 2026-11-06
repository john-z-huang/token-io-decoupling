# Complete Coding Routes

[English](README.md) | [简体中文](README_zh_cn.md)

Layer-04 separates reusable execution modules from route composition. Each Single-Agent or Multi-Agent route calls the same ordered module chain, with one mode-specific execution module. A module owns its consumed lower-layer checks and returns evidence/continuation to its caller; the route owns cross-module order, caller position, and changed-epoch loops. Modules do not call sibling modules.

## Entry

Select only the authorized route from the [route index](INDEX.md). Routes own cross-module order and continuation; the module catalog is for selecting one authorized module at a time when the task permits it.
