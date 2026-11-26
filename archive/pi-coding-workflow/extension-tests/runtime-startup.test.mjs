import assert from 'node:assert/strict';
import { test } from 'node:test';
import { releaseSlice, harness } from './pi-runtime-fixture.mjs';

test('extension is passive before explicit opt-in and does not write configuration or state', async () => {
  const h = harness();
  assert.equal(h.isEnabled(), false);
  const messages = [{ role: 'user', content: 'hello' }];
  assert.deepEqual((await h.emit('context', { messages })).messages, messages);
  assert.equal((await h.invoke('bash', {})).isError, false);
  assert.equal(h.entries.length, 0);
});
test('command explicitly selects mode/count without creating a child', async () => {
  const h = harness();
  await h.start('multi 2 合成任务');
  assert.equal(h.w().state.mode, 'multi');
  assert.equal(h.w().state.childCount, 2);
  assert.equal(h.calls.length, 0);
  assert.equal(h.messages.at(-1).opts.triggerTurn, true);
});
test('CLI flags start only from actual user input, preserving other system prompt sections', async () => {
  const h = harness({ flags: { 'coding-mode': 'single', 'coding-audit-defaults': true } });
  await h.emit('before_agent_start', { messageType: 'custom', systemPromptOptions: { sections: {} } });
  assert.equal(h.w(), undefined);
  const options = { sections: { existing: 'keep' } };
  await h.emit('before_agent_start', {
    messageType: 'user',
    prompt: '真实合成用户目标',
    systemPromptOptions: options,
  });
  assert.ok(h.w());
  assert.equal('task' in h.entries.at(-1).data.state, false);
  assert.equal(options.sections.existing, 'keep');
  assert.ok(options.sections.coding_workflow);
});

const command = (h, args) => h.commands.get('coding').handler(args, h.ctx);
for (const mode of ['single', 'multi'])
  test(`startup registry asks mode then audit for ${mode}`, async () => {
    const prompts = [],
      choices = [
        mode === 'multi' ? 'multi（默认预算1）' : 'single',
        '使用默认（balanced / milestone_only / full）',
      ];
    const h = harness({
      hasUI: true,
      select: async (title, values) => {
        prompts.push(title);
        assert.ok(values.includes(choices[0]));
        return choices.shift();
      },
    });
    await command(h, 'start 合成启动');
    assert.ok(h.w());
    assert.match(prompts[0], /1\. Coding/);
    assert.match(prompts[1], /2\. 审计/);
    assert.equal(h.w().state.childCount, mode === 'multi' ? 1 : 0);
    assert.deepEqual(h.w().state.audit.source, {
      audit_mode: 'default',
      root_reasoning_cadence: 'default',
      worker_reasoning_cadence: 'default',
    });
  });
test('explicit fields skip questions; custom remaining fields have separate sources', async () => {
  const prompts = [],
    choices = ['定制未提供字段', 'off'];
  const h = harness({
    hasUI: true,
    select: async (title) => {
      prompts.push(title);
      return choices.shift();
    },
  });
  await command(h, 'multi 2 --audit-mode economy --worker-cadence milestone_only 显式任务');
  assert.equal(prompts.length, 2);
  assert.equal(prompts[1], 'root_reasoning_cadence');
  assert.equal(h.w().state.audit.root_reasoning_cadence, 'off');
  assert.ok(Object.values(h.w().state.audit.source).every((s) => s === 'explicit'));
  const context = await h.emit('context', { messages: [] });
  assert.match(context.messages[0].content, /"audit_mode":"economy"/);
  const status = await h.invoke('coding_checkpoint', { action: 'status' });
  assert.match(status.result.content[0].text, /"audit"/);
});
test('defaults only apply to missing fields and never overwrite explicit ones', async () => {
  const h = harness();
  await command(h, 'single --audit-mode full --audit-defaults task');
  assert.equal(h.w().state.audit.audit_mode, 'full');
  assert.equal(h.w().state.audit.source.audit_mode, 'explicit');
  assert.equal(h.w().state.audit.source.root_reasoning_cadence, 'default');
});
for (const choices of [
  [undefined],
  ['multi（默认预算1）', undefined],
  ['single', '定制未提供字段', undefined],
])
  test(`cancel at ${choices.length} leaves no workflow or effects`, async () => {
    const h = harness({ hasUI: true, select: async () => choices.shift() });
    await command(h, 'start task');
    assert.equal(h.w(), undefined);
    assert.equal(h.entries.length, 0);
    assert.equal(h.calls.length, 0);
    assert.equal((await h.invoke('bash', {})).isError, false);
  });
test('failed manual startup is passive, while missing CLI answers allow reads and block effects', async () => {
  for (const args of [
    'start task',
    'single task',
    'multi 0 --audit-defaults task',
    'multi -1 --audit-defaults task',
    'multi 1.5 --audit-defaults task',
    'single --audit-mode unknown --audit-defaults task',
    'multi --count NaN --audit-defaults task',
  ]) {
    const h = harness();
    await command(h, args);
    assert.equal(h.w(), undefined, args);
    assert.equal(h.entries.length, 0);
    assert.equal((await h.invoke('read', {})).isError, false, args);
    assert.deepEqual((await h.emit('context', { messages: [] })).messages, []);
  }
  const h = harness({ flags: { 'coding-mode': 'single' } });
  await h.emit('before_agent_start', {
    messageType: 'user',
    prompt: 'task',
    systemPromptOptions: { sections: {} },
  });
  assert.equal(h.w(), undefined);
  assert.equal((await h.invoke('read', {})).isError, false);
  assert.equal((await h.invoke('bash', {})).isError, true);
});
test('startup race is serialized and cancel invalidates late UI results', async () => {
  let answerAudit;
  const h = harness({
    hasUI: true,
    select: () =>
      new Promise((resolve) => {
        answerAudit = resolve;
      }),
  });

  const pending = command(h, 'single task');
  assert.equal((await h.invoke('bash', {})).isError, true);
  await command(h, 'single --audit-defaults competing');
  assert.equal(h.w(), undefined);

  await command(h, 'cancel');
  await command(h, 'single --audit-defaults replacement');
  const replacementRun = h.w().state.runId;
  answerAudit('使用默认（balanced / milestone_only / full）');
  await pending;

  assert.equal(h.w().state.runId, replacementRun);
  assert.equal(h.entries.length, 1);
  assert.equal(h.messages.filter((message) => message.opts?.triggerTurn).length, 1);
});
test('tree navigation while UI is open prevents stale startup commit', async () => {
  let answerAudit;
  const h = harness({
    hasUI: true,
    select: () =>
      new Promise((resolve) => {
        answerAudit = resolve;
      }),
  });

  const pending = command(h, 'single task');
  await Promise.resolve();
  await h.emit('session_tree');
  answerAudit('使用默认（balanced / milestone_only / full）');
  await pending;

  assert.equal(h.w(), undefined);
  assert.equal(h.entries.length, 0);
});
for (const volatile of [false, true])
  test(`confirmed answers survive tasks/reload/tree without budget refund, volatile=${volatile}`, async () => {
    const h = harness({ flags: { 'coding-volatile': volatile } });
    await command(h, 'multi --audit-defaults task');

    await releaseSlice(h);
    await h.invoke('coding_delegate', {
      revision: h.w().state.revision,
      tool: 'subagent',
      evidence: [h.userRef()],
      jobs: [{ role: 'Primary Output', agent: 'worker', task: 'task', paths: [] }],
    });
    assert.match(
      h.calls.find((c) => c.name === 'subagent').input.calls[0].prompt,
      /会话审计偏好及每字段来源/,
    );

    await command(h, 'start second task');
    assert.equal(h.w().state.allocations.length, 1);
    const audit = structuredClone(h.w().state.audit);
    await h.emit('session_start', { reason: 'reload' });
    assert.deepEqual(h.w().state.audit, audit);
    await h.emit('session_tree');
    assert.equal(h.w().state.allocations.length, 1);
    const readback = await h.invoke('read', { path: 'synthetic.ts' });
    const resumed = await h.invoke('coding_checkpoint', {
      action: 'resume',
      revision: h.w().state.revision,
      evidence: [readback.toolCall.id],
    });
    assert.equal(resumed.isError, false, resumed.result.content[0].text);

    await command(h, 'start third task');
    assert.deepEqual(h.w().state.audit, audit);
    assert.equal(h.w().state.allocations.length, 1);
    if (volatile) assert.equal(h.entries.length, 0);
    h.setSessionId('fresh-fork');
    await h.emit('session_start', { reason: 'fork' });
    await command(h, 'start fork task');
    assert.equal(h.w(), undefined);
  });
test('answers survive navigation before the first workflow branch entry', async () => {
  const h = harness();
  await command(h, 'single --audit-defaults task');
  h.setBranch([]);
  await h.emit('session_tree');
  assert.equal(h.w(), undefined);
  await command(h, 'start second task');
  assert.ok(h.w());
});
test('a fresh extension instance restores confirmed answers and rejects corrupted answer envelopes', async () => {
  const h = harness();
  await command(h, 'multi 2 --audit-defaults task');

  const reloaded = harness({ entries: h.entries });
  await reloaded.emit('session_start', { reason: 'resume' });
  assert.equal(reloaded.getRestoreError(), '');
  assert.equal(reloaded.w().state.status, 'paused');
  assert.equal(reloaded.w().state.childCount, 2);
  const bad = structuredClone(h.entries);
  bad.at(-1).data.state.audit.audit_mode = 'invalid';
  const corrupt = harness({ entries: bad });
  await corrupt.emit('session_start', { reason: 'resume' });
  assert.match(corrupt.getRestoreError(), /审计启动快照无效/);
  await command(corrupt, 'single --audit-defaults reset');
  assert.equal(corrupt.w(), undefined);
});
test('volatile lost-state reload/resume blocks without appending a fake recovery entry', async () => {
  for (const reason of ['reload', 'resume']) {
    const h = harness({
      flags: { 'coding-volatile': true },
      entries: [
        {
          type: 'custom_message',
          customType: 'token-io.coding-hooks.v1.start',
          details: { sessionId: 'runtime-test' },
        },
      ],
    });
    await h.emit('session_start', { reason });
    assert.match(h.getRestoreError(), /volatile/);
    await command(h, 'multi --audit-defaults task');
    assert.equal(h.w(), undefined);
    assert.equal(h.entries.length, 1);
    assert.equal((await h.invoke('bash', {})).isError, true);
    h.setSessionId('fresh-session');
    await h.emit('session_start', { reason: 'new' });
    await command(h, 'multi --audit-defaults task');
    assert.ok(h.w());
    assert.equal(h.entries.length, 1);
  }
});
for (const reason of ['reload', 'resume'])
  test(`volatile storage flag alone never opts in on ${reason}`, async () => {
    const h = harness({ flags: { 'coding-volatile': true } });
    await h.emit('session_start', { reason });
    assert.equal(h.getRestoreError(), '');
    assert.equal(h.isEnabled(), false);
    assert.equal((await h.invoke('bash', {})).isError, false);
    assert.equal(h.entries.length, 0);
  });
test('headless explicit audit fields skip menus without marking them default', async () => {
  const h = harness();
  await command(
    h,
    'start --mode multi --count 2 --audit-mode economy --root-cadence off --worker-cadence milestone_only task',
  );
  assert.ok(h.w());
  assert.equal(h.w().state.childCount, 2);
  assert.ok(Object.values(h.w().state.audit.source).every((s) => s === 'explicit'));
});
test('CLI does not implicitly restart a running task and late cancellation cannot poison a replacement', async () => {
  let release;
  const h = harness({
    flags: { 'coding-mode': 'single' },
    hasUI: true,
    select: () =>
      new Promise((r) => {
        release = r;
      }),
  });
  const event = (prompt) => ({ messageType: 'user', prompt, systemPromptOptions: { sections: {} } });
  const pending = h.emit('before_agent_start', event('initial'));
  await Promise.resolve();
  await command(h, 'cancel');
  await command(h, 'single --audit-defaults replacement');
  const id = h.w().state.runId;
  release('使用默认（balanced / milestone_only / full）');
  await pending;
  assert.equal(h.w().state.runId, id);
  assert.equal((await h.invoke('read', {})).isError, false);

  await h.emit('before_agent_start', event('later'));
  assert.equal(h.w().state.runId, id);
  assert.equal(h.w().state.status, 'active');
  await command(h, 'start explicitly requested later task');
  assert.notEqual(h.w().state.runId, id);
});
test('custom budget input cancellation and invalid answers never fall back to one', async () => {
  for (const count of [undefined, '', '0', '-1', '1.1', '9007199254740992']) {
    const h = harness({ hasUI: true, select: async () => 'multi（自定义数量）', input: async () => count });
    await command(h, 'start task');
    assert.equal(h.w(), undefined);
    assert.equal(h.entries.length, 0);
  }
  const h = harness({ hasUI: true, select: async () => 'single' });
  await command(h, 'start --count 2 --audit-defaults task');
  assert.equal(h.w(), undefined);
});
test('cancel during mode question does not open a later audit dialog', async () => {
  let release,
    selects = 0;
  const h = harness({
    hasUI: true,
    select: () => {
      selects++;
      return new Promise((r) => {
        release = r;
      });
    },
  });
  const pending = command(h, 'start task');
  await command(h, 'cancel');
  release('single');
  await pending;
  assert.equal(selects, 1);
  assert.equal(h.w(), undefined);
});
test('default extension never takes over normal input', async () => {
  const h = harness();
  await h.emit('before_agent_start', {
    messageType: 'user',
    prompt: 'task',
    systemPromptOptions: { sections: {} },
  });
  assert.equal(h.w(), undefined);
  assert.equal(h.entries.length, 0);
  assert.equal((await h.invoke('read', {})).isError, false);
});

test('explicit next task reuses session budget without finish and refuses unresolved effects', async () => {
  const h = harness();
  await h.start('multi 初始任务');
  await releaseSlice(h);
  const first = h.w().state;
  const delegated = await h.invoke('coding_delegate', {
    revision: first.revision,
    tool: 'subagent',
    evidence: [h.userRef()],
    jobs: [{ role: 'Primary Output', agent: 'worker', task: 'one shot', paths: [] }],
  });
  assert.equal(delegated.isError, false);
  first.inFlight.push('pending');
  await command(h, 'start 用户请求的新任务');
  assert.equal(h.w().state.runId, first.runId);
  first.inFlight.pop();
  await command(h, 'start 用户请求的新任务');
  assert.notEqual(h.w().state.runId, first.runId);
  assert.equal(first.status, 'active');
  assert.match(h.messages.at(-1).message.content, /用户请求的新任务/);
  assert.equal(h.w().state.slice, undefined);
  assert.deepEqual(h.w().state.allocations, first.allocations);
});
