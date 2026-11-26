#!/usr/bin/env node
// Explicit installed-contract check. Never execute the plugin tool or launch a child process.
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import {
  resolveSubagentAdapter,
  subagentInput,
  subagentModelInput,
} from '../extensions/coding-workflow/subagent-adapter.ts';
import { createHostLoader, hostModulePaths, loadTypeBoxCheck, openPiHost } from './pi-installed-host.mjs';

const hostLocation = process.argv[2] ?? process.env.PI_EXTENSION_HOST_ROOT;
const entry = process.argv[3];
assert.ok(
  hostLocation && entry,
  '传入已有 Pi 包根与 @mjakl/pi-subagent@3.1.0/index.ts；不自动安装或发现配置',
);
const host = openPiHost(hostLocation);
const pluginEntry = resolve(entry);
const pluginRoot = dirname(pluginEntry);
const pluginMetadata = JSON.parse(readFileSync(join(pluginRoot, 'package.json'), 'utf8'));
assert.equal(pluginMetadata.name, '@mjakl/pi-subagent');
assert.equal(pluginMetadata.version, '3.1.0', '其他版本须重新审阅契约');
const jiti = createHostLoader(host, import.meta.url, hostModulePaths(host));
const plugin = await jiti.import(pluginEntry);
const tools = [],
  handlers = new Map();
plugin.default({
  registerFlag() {},
  getFlag() {},
  on(name, handler) {
    handlers.set(name, handler);
  },
  registerTool(tool) {
    tools.push(tool);
  },
});
const tool = tools.find((t) => t.name === 'subagent');
assert.ok(tool, '插件应在合成根上下文注册 subagent');
const adapter = resolveSubagentAdapter(tool.parameters);
assert.ok(adapter, '实际工具须注册可用的 calls[] Schema');
const check = await loadTypeBoxCheck(host);
const { buildPiArgs } = await jiti.import(join(pluginRoot, 'runner.ts'));
const agent = {
  name: 'synthetic',
  description: 'synthetic',
  thinking: 'high',
  systemPrompt: '',
  source: 'user',
  filePath: 'synthetic.md',
};

for (const [provider, model, thinking] of [
  ['openai', 'gpt-6.1-sol', 'medium'],
  ['openai', 'gpt-6.1-terra', 'high'],
  ['openai', 'gpt-6-luna', 'off'],
  ['custom-provider', 'nested/gpt-6-luna', 'low'],
]) {
  const input = subagentInput({
    agent: agent.name,
    task: 'verbatim\n合成任务',
    cwd: process.cwd(),
    modelInput: subagentModelInput(adapter, `${provider}/${model}:${thinking}`),
  });
  assert.equal(check(tool.parameters, input), true, JSON.stringify(input));
  const normalized = plugin.normalizeCalls(input.calls, process.cwd());
  assert.equal(normalized.error, undefined);
  assert.equal(normalized.calls.length, 1);
  const [call] = normalized.calls;
  assert.equal(call.prompt, 'verbatim\n合成任务');
  assert.equal(call.initialContext, 'empty');
  assert.equal(call.sessionHandle, undefined);
  const args = buildPiArgs(
    agent,
    null,
    call.prompt,
    call.initialContext,
    null,
    undefined,
    undefined,
    call.model,
    { provider: 'openai', id: 'gpt-6-luna' },
    false,
    call.thinking,
  );
  assert.equal(args[args.lastIndexOf('--model') + 1], `${provider}/${model}`);
  assert.equal(args[args.lastIndexOf('--thinking') + 1], thinking, '调用档位必须覆盖 agent 默认 high');
  assert.ok(args.includes('--no-session'));
  assert.ok(!args.includes('--session-id'));
  assert.ok(!args.includes('--fork'));
}
const inherited = subagentInput({
  agent: agent.name,
  task: 'inherit',
  cwd: process.cwd(),
  modelInput: subagentModelInput(adapter),
});
assert.equal(check(tool.parameters, inherited), true);
assert.equal('model' in inherited.calls[0], false);
assert.equal('thinking' in inherited.calls[0], false);
// Failure normalization is supplied by the plugin's host event handler, not by bypassing it.
const resultHook = handlers.get('tool_result');
assert.equal(typeof resultHook, 'function');
assert.deepEqual(
  await resultHook({ toolName: 'subagent', details: { kind: 'pi-subagent', failed: true, results: [] } }),
  { isError: true },
);
assert.equal(
  await resultHook({ toolName: 'subagent', details: { kind: 'pi-subagent', results: [] } }),
  undefined,
);
console.log(
  `Pi ${host.version} / @mjakl/pi-subagent ${pluginMetadata.version}：真实注册 Schema、参数规范化、模型/thinking CLI 与失败 Hook 契约通过；未执行插件工具、Pi 子进程、API 或配置写入。`,
);
