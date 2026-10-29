# Coding 路线入口

[English](route-entry.md) | [简体中文](route-entry_zh_cn.md)

本检查点负责路线前验证组合及唯一获授权路线选择结果。

## 触发与输入

Coding 入口在[Contract 检查点](../layer-02-workflow-concepts/entry-and-context/contract_zh_cn.md)、[Environment 检查点](../layer-02-workflow-concepts/entry-and-context/environment_zh_cn.md)、[能力清单](../layer-02-workflow-concepts/entry-and-context/environment-capability-inventory_zh_cn.md)和[Mode 检查点](../layer-02-workflow-concepts/entry-and-context/mode_zh_cn.md)通过后调用本检查点。输入为各项当前结果，包括已释放的 mode/count 及未解决的失败。

## 决策与结果

确认门禁均已完成，只选择 Mode 授权的路线，并将路线标识和门禁证据传给路线入口。将所选路线标识和门禁证据返回 Coding 入口，由入口链接该路线；路线在 S03/M03 核对该结果。

## 失败边界

若前置项缺失、矛盾或尚未释放，返回对应入口检查点并停止依赖该结果的路线工作。不得重新解释 Mode、选择后备路线或在此初始化路线专用状态。

## 相关概念

- [Mode](../layer-02-workflow-concepts/entry-and-context/mode_zh_cn.md)
