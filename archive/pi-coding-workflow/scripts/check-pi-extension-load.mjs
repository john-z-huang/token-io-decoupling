#!/usr/bin/env node
// Isolated host-module smoke: no Pi session, global settings, MCP connection, model or network call.
import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';
import { createHostLoader, discoverPiHostRoot, loadTypeBoxCheck, openPiHost } from './pi-installed-host.mjs';

const host = openPiHost(discoverPiHostRoot());
const jiti = createHostLoader(host, import.meta.url, {
  typebox: host.requireHost.resolve('typebox'),
});
const entry = fileURLToPath(new URL('../extensions/coding-workflow/index.ts', import.meta.url));
const factory = await jiti.import(entry, { default: true });
const tools = [],
  commands = [],
  events = [],
  flags = [];
factory({
  on: (name) => events.push(name),
  registerFlag: (name) => flags.push(name),
  registerCommand: (name) => commands.push(name),
  registerTool: (tool) => tools.push(tool),
});
assert.deepEqual(
  tools.map((t) => t.name),
  ['coding_checkpoint', 'coding_slice', 'coding_run', 'coding_delegate'],
);
assert.ok(
  !events.includes('agent_before_settle') &&
    events.includes('agent_settled') &&
    events.includes('context') &&
    events.includes('tool_call'),
);
assert.ok(!events.includes('session_switch') && !events.includes('session_fork'));
assert.equal(commands[0], 'coding');
assert.equal(flags.length, 7);
const check = await loadTypeBoxCheck(host);
assert.equal(check(tools[0].parameters, { action: 'status' }), true);
assert.equal(
  check(tools[0].parameters, { action: 'rules', document: 'verification-epoch', fragment: 'actions' }),
  true,
);
assert.equal(check(tools[0].parameters, { action: 'rules', fragment: 3 }), false);
assert.equal(
  check(tools[0].parameters, {
    action: 'report',
    revision: 0,
    reports: [{ checkpoint: 'ER01', outcome: 'complete', summary: 'old schema', evidence: ['source'] }],
  }),
  false,
);
for (const input of [
  { action: 'verify', revision: 0, evidence: ['check'] },
  { action: 'signal', revision: 0, signal: 'capability_changed', reason: 'test', evidence: ['source'] },
  { action: 'finish', revision: 0 },
]) {
  assert.equal(check(tools[0].parameters, input), false);
}
assert.equal(
  check(tools[2].parameters, {
    revision: 0,
    tool: 'bash',
    input: {},
    effect: 'git',
    rationale: 'test',
    evidence: ['source'],
    verificationEvidence: ['check'],
  }),
  true,
);
assert.equal(
  check(tools[2].parameters, {
    revision: 0,
    tool: 'bash',
    input: {},
    effect: 'fake',
    rationale: 'test',
    evidence: ['source'],
  }),
  false,
);
console.log(
  `Pi ${host.version} 提供的 Jiti/TypeBox：入口加载、注册及 Schema smoke 通过；非真实客户端/子代理/Memory 集成验收。`,
);
