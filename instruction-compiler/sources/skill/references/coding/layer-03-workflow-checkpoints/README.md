# Layer-03 Workflow Checkpoints

[English](README.md) | [简体中文](README_zh_cn.md)

This directory owns task-specific applicability and readiness decisions for Layer-04 route and bounded-module invocations. It does not redefine Layer-01 policies or Layer-02 pass conditions, and it does not schedule Layer-04 routes or modules.

Layer-03 owners state semantic prerequisites, results, and failure boundaries without depending on numbered route coordinates. A route or module caller supplies the current requirements and owns any mapping or scheduling decision.

## Entry

Use [INDEX](INDEX.md) to select a checkpoint. Route and module callers consume these owners at their applicable checkpoint or substep and record the returned evidence.
