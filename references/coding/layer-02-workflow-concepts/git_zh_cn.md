# Git 检查点

[English](git.md) | [简体中文](git_zh_cn.md)

## 动作

1. 确认准确的仓库、worktree、分支或 ref、远程、操作和计划产生的外部影响。
2. 修改 Git 状态前检查 status 和相关历史，不要纳入用户无关的现有修改。
3. 将 commit、push、Issue、PR、远程配置修改和其他外部影响分开处理，除非每项影响都得到明确授权。
4. 目标不明确、出现意外冲突、缺少授权或前置条件失败时停止；不要扩大操作范围来恢复。

## 通过条件

获授权的 Git 操作已针对准确目标完成，或已报告不可用的授权、冲突或前置条件。

## 边界

本检查点不授予产品决策权限，不允许未请求的清理，也不会把可能产生的 Git 影响变成已授权影响。

## 相关概念

- [Coding Context Exchange 工作区边界](../layer-01-fundamental-concepts/context-exchange-workspace-boundary_zh_cn.md) — 定位 worktree、权限和路径边界。
- [Coding Session 职责归属](../layer-01-fundamental-concepts/session-role-ownership_zh_cn.md) — 定位 Documentation/Comments & Git Operations 归属。
- [Coding Execution Control](../layer-01-fundamental-concepts/execution-control_zh_cn.md) — 定位授权范围和未发布边界归属。
- [Coding Delegation State Record Worker Boundary](../layer-01-fundamental-concepts/delegation-state-record-worker-boundary_zh_cn.md) — 定位父级控制路径和 Worker 访问边界。
