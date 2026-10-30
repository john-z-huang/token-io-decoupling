# 完整 Coding 路线

[English](README.md) | [简体中文](README_zh_cn.md)

Layer-04 将可复用执行模块与路线组合分开。每条 Single-Agent 或 Multi-Agent 路线调用相同的有序模块链，其中执行模块按模式选择。模块负责其消费的低层检查，并向调用方返回证据/continuation；路线负责跨模块顺序、调用方位置和 epoch 变化循环。模块不得调用同级模块。

## 入口

仅从[路线索引](INDEX_zh_cn.md)选择获授权路线。路线负责跨模块顺序和 continuation；任务允许时，可从模块目录单独选择一个已授权模块。
