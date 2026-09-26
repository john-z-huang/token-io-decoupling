# 控制边界检查点

[English](control.md) | [简体中文](control_zh_cn.md)

## 动作

1. 消费 Stage Feedback owner 的压缩 Progress Signal，补充当前 `Unreleased boundary`，不额外生成第二份进度报告。
2. 检查下一动作是否跨越接口、schema、兼容性、安全、风险、难以逆转修改、范围或外部影响边界。
3. 需要更多证据时发出 Evidence-on-Demand，并**暂停**放行；取得证据后返回本检查点。这是中间动作，不是第四种最终授权结果。
4. 最终只选择 `Continue`、`Amend` 或 `Stop`；只有明确的 `Continue` 才放行已批准范围内的下一 Slice，`Amend` 返回 Contract 与 Decision。单代理作为逻辑暂停；多代理由父级控制放行。

## 通过条件

下一步要么已在当前范围内发布，要么已暂停并明确需要的修改、证据、能力或授权。

## 边界

本检查点控制发布和权限，不静默批准范围扩大，不替代验证，也不授予 Git 或外部影响授权。

## 相关概念

- [Coding Execution Control](../layer-01-fundamental-concepts/execution-control_zh_cn.md) — 定位 Interaction Slice 和控制边界归属。
- [Coding Execution Decision Gate](../layer-01-fundamental-concepts/execution-decision-gate_zh_cn.md) — 定位决策和放行条件归属。
- [Coding Delegation State Record Worker Boundary](../layer-01-fundamental-concepts/delegation-worker-boundary_zh_cn.md) — 定位父级控制的 Worker 放行边界。
