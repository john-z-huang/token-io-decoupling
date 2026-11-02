# 优化基准

[English](OPTIMIZATION_BENCHMARK.md) | [简体中文](OPTIMIZATION_BENCHMARK_zh_cn.md)

本文档负责 Issue #182 服务组件基准的测量方法和实测结果，不定义工作流权限、生产配置或完整 Agent 成本模型。

## 测量边界

基线参考调用方接收完整、已核实的相关事实；辅助调用方接收实际组件结果、已核实事实及所用工具的实际描述和请求 payload schema。两组具有相同语义目标和冻结的正确性判据。

这是 Python 服务组件层的直接测量，不代表当前 Root Agent 用量、完整 Agent 会话、MCP 传输开销、真实宿主授权或货币成本。Server 初始化、未使用工具的元数据、MCP envelope/传输、事实收集及完整 Agent 推理不在比较范围内。API 调用耗时不含夹具建立；逐案例 elapsed 包含建立夹具与本地来源/harness 工作。重叠子层不得相加，也不能据此宣称端到端提速。

[固定数据集](benchmarks/issue_182_cases.json)采用数据格式 schema version 1、评估协议 version 2：

| 场景 | 必需语义结果 |
| --- | --- |
| 有界验证规则 | 仍需当前 Verification；预检不能替代它。 |
| 锁定的多代理阶段建议 | 入口和 Session 已就绪、工作定义待完成，应映射到工作定义模块；建议不授予权限。 |
| 通用候选预检 | 有界新候选在可信的不存在基线下通过适用结构检查。 |
| Skill 语言违规 | 拒绝包含无效跨语言 Related 链接的双语候选。 |
| Skill 指令物化 | 经所选路径将获准的 Fact Markdown 写为准确预期字节。 |

更广的 Single/Multi、缺失 reader、权限、冲突、恢复和 epoch 矩阵仍由单元及集成测试覆盖。这个小数据集是描述性证据，不是通用工作负载估计。

## 控制条件与正确性

采集前冻结事实、提示词、输出 schema、预期结果及来源/元数据哈希。每个场景的每组使用独立临时项目/状态夹具。采集期间来源变化会使比较失效。

物化基线返回获准内容，由有界本地 harness 写入。辅助组使用实际 prepare、同一 manifest 检查、新鲜 whole-batch 预检、重新核验授权/基线及准确应用。共同判据核对独立预期字节和最终文件系统状态。辅助组 StateService 是真实实现，宿主绑定和操作员授权是合成夹具；基线 harness 未使用 StateService。两者都不证明生产授权。

符合预期的拒绝是正确负面结果，不代表文件效果已完成。每个案例采用独立闭合答案域：“是否需要最终验证”不能代替“结构预检状态”。文件效果由实际文件系统证据判定，异常路径也相同，不作为模型输出评分字段；不可读证据保持 unknown。

分别记录首次正确性、有界语义修复和最终正确性。每个场景/组最多一次语义修复，不重试服务方错误，不在采集后追加案例，不为有利数字选择性重跑。顺序运行最多 30 次传输尝试，达到上限后的剩余工作标为未运行。

参考调用方请求 gpt-6-luna、medium、零自动重试，输出最多 4,000 tokens，显式使用进程中非空的 OPENAI_API_KEY 和 OPENAI_BASE_URL。内层调用保留生产契约：路由器超时 20 秒且 Decisions 无 reasoning 参数；物化器超时 30 秒、medium。可见时记录请求/实际报告设置，不可见则未知。禁止保存凭据、端点值、请求头或原始服务方错误。

## 指标与解读

分别记录调用方和工具内 API 实际报告的输入、输出、总 token。缺失或不可见用量为 null；明确无调用的路径记录零次调用和 null 用量。不完整遥测须保留覆盖信息，不能冒充完整合计。

分别计数逻辑 API 调用、含失败在内的实际 HTTP 尝试及组件调用。参数/结果 UTF-8 字节数不是 token。假响应测试只验证机制，不提供实测数据。

分别报告 API、组件、夹具建立、harness 和 apply 耗时。基线本地写入与受控 apply 采用不同路径。分别比较调用方 token 和调用方加内层 token；调用方输出下降可能伴随总输入、token 或调用次数增加。只有来源当前有效、遥测完整且语义判据通过时，才可比较效率。

## 实测结果

协议 2 于 2026-11-02 15:49:32–15:50:09 UTC 运行。两组均首次通过 5/5：各为 0/5 修复、0/5 失败。十行全部执行；来源、数据集及元数据指纹稳定，12 次 API 请求的用量遥测完整。请求和实际报告的模型 ID 均为 gpt-6-luna。

| 五案例合计指标 | 基线 | 辅助组 |
| --- | ---: | ---: |
| 调用方输入 tokens | 11,028 | 12,930 |
| 调用方输出 tokens | 859 | 544 |
| 调用方总 tokens | 11,887 | 13,474 |
| 工具内输入 / 输出 / 总 tokens | —（未调用） | 2,874 / 43 / 2,917 |
| 所有 API 总 tokens | 11,887 | 16,391 |
| 调用方 / 工具内 API 次数 | 5 / 0 | 5 / 2 |
| 实际 HTTP 尝试次数 | 5 | 7 |
| 调用方 API 调用耗时 | 17,119.916 ms | 14,943.883 ms |
| 工具内 API 调用耗时 | —（未调用） | 4,113.276 ms |
| 所有 API 调用耗时合计 | 17,119.916 ms | 19,057.159 ms |

调用方输出下降 36.7%，调用方输入增加 17.2%，所有 API 总 token 增加 37.9%。调用从五次增至七次，API 调用耗时合计增加 11.3%。这些数据不能证明整体 token 节省或端到端提速。这里计入了元数据/schema 和两个内层请求；小样本不能隔离或泛化其影响，也不主张价格或缓存调整后的成本。

辅助组有七次直接组件调用：一次规则读取、一次路由、两次预检、三次物化操作。参数共 2,978 UTF-8 字节，结果共 14,732 字节。基线文件 harness 为 0.001273 秒，受控 apply 为 0.009417 秒，辅助物化建立夹具为 0.109502 秒。这些不同应用路径不构成等价耗时比较，完整逐行/分层时间仍保留。

[协议 2 原始报告](benchmarks/issue_182_live_protocol2_2026-11-02.json)用于主要比较。[协议 1 原始报告](benchmarks/issue_182_live_2026-11-02.json)仅供审计：15 次请求、7/10 评分通过、三次修复尝试。其共享答案词表混合了可重叠属性，不能据此评价质量或效率；原比较标志早于语义有效性门禁。只进行了一次协议修正和完整补测，事实、任务、模板、预期字节、模型、强度及预算均保留，没有为有利数字继续选跑。

[协议 1 manifest](benchmarks/protocol_v1/manifest.json)通过哈希绑定原[数据集](benchmarks/protocol_v1/issue_182_cases.json)、[案例源码](benchmarks/protocol_v1/benchmark_cases.py.txt)、[计量源码](benchmarks/protocol_v1/benchmark_metrics.py.txt)及[运行入口源码](benchmarks/protocol_v1/optimization_benchmark.py.txt)。归档源码文本仅供参考，不是执行入口。

## 复现

先审阅[运行入口](tests/support/optimization_benchmark.py)和[数据集](benchmarks/issue_182_cases.json)。授权真实请求并配置两项进程变量后，从 mcp/ 使用未存在的输出路径运行：

```sh
uv run --no-sync --package token-io-decoupling python tests/support/optimization_benchmark.py --live --output benchmarks/new_authorized_run.json
```

没有 live opt-in 不发送测量请求；输出已存在会在 API 前拒绝。复现只能得到另一描述性样本，不能保证上述数值。此过程不使用 Codex SDK；fresh CLI 检查由独立有序最终入口负责。

## 相关指南

- [工作流路由](WORKFLOW_ROUTING_zh_cn.md)
- [候选合规](CANDIDATE_COMPLIANCE_zh_cn.md)
- [输出物化](OUTPUT_MATERIALIZATION_zh_cn.md)
