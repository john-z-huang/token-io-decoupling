# Layer-03 工作流检查点

[English](README.md) | [简体中文](README_zh_cn.md)

本目录负责 Layer-02 检查点与完整 Layer-04 路线之间、针对当前任务的适用性和路由决策；不重新定义 Layer-01 政策或 Layer-02 通过条件。

Layer-03 owner 只描述语义前置条件、结果和失败边界，不依赖编号路线坐标。调用方路线负责将这些 owner 映射到自己的编号步骤。

## 入口

使用 [INDEX](INDEX_zh_cn.md) 选择检查点。路线文档在编号步骤中消费这些 owner。
