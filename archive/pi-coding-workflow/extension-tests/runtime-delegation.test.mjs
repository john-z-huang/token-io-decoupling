import assert from 'node:assert/strict';
import { test } from 'node:test';
import { compatibleSubagent } from '../extensions/coding-workflow/runtime.ts';
import { releaseSlice, body, callsSchema, harness } from './pi-runtime-fixture.mjs';

test('real delegate adapter performs one synchronous call and records no fabricated child Session ID', async () => {
  const h = harness();
  await h.start('multi 合成实现任务');

  await releaseSlice(h);
  const result = await h.invoke('coding_delegate', {
    revision: h.w().state.revision,
    tool: 'subagent',
    evidence: [h.userRef()],
    jobs: [{ role: 'Primary Output', agent: 'worker', task: '执行已放行的合成任务', paths: [] }],
  });
  assert.equal(result.isError, false);
  assert.equal(h.calls.filter((c) => c.name === 'subagent').length, 1);
  assert.equal(h.w().state.allocations[0].status, 'completed');
  assert.equal('sessionId' in h.w().state.allocations[0], false);
  assert.match(h.calls.find((c) => c.name === 'subagent').input.calls[0].prompt, /禁止创建\/派发其他代理/);
});
test('delegate rejects a write path when the current Slice does not allow its effect', async () => {
  const h = harness();
  await h.start('multi 合成只读切片');

  await releaseSlice(h);
  h.w().state.slice.mutations = ['read'];
  const result = await h.invoke('coding_delegate', {
    revision: h.w().state.revision,
    tool: 'subagent',
    evidence: [h.userRef()],
    jobs: [{ role: 'Primary Output', agent: 'worker', task: 'synthetic', paths: ['synthetic.ts'] }],
  });
  assert.match(result.result.content[0].text, /影响未被当前 Slice 放行/);
  assert.equal(h.calls.filter((c) => c.name === 'subagent').length, 0);
  assert.equal(h.w().state.allocations.length, 0);
});
test('calls[] adapter maps prompt and explicit thinking without creating a named session', async () => {
  const h = harness();
  await h.start('multi 合成3.1接口');

  await releaseSlice(h);
  const result = await h.invoke('coding_delegate', {
    revision: h.w().state.revision,
    tool: 'subagent',
    evidence: [h.userRef()],
    jobs: [
      {
        role: 'Primary Output',
        agent: 'worker',
        task: '执行新版合成任务',
        paths: [],
        model: 'openai/gpt-6.1-sol:medium',
        modelReason: '显式选择不可被代理默认high覆盖',
      },
    ],
  });
  assert.equal(result.isError, false, JSON.stringify(result));
  const calls = h.calls.filter((c) => c.name === 'subagent');
  assert.equal(calls.length, 1);
  assert.ok(calls[0].parentToolCallId);
  const input = calls[0].input;
  assert.deepEqual(Object.keys(input), ['calls']);
  assert.equal(input.calls.length, 1);
  const [call] = input.calls;
  assert.equal(call.agent, 'worker');
  assert.equal(call.cwd, process.cwd());
  assert.equal(call.initialContext, 'empty');
  assert.equal(call.model, 'openai/gpt-6.1-sol');
  assert.equal(call.thinking, 'medium');
  assert.match(call.prompt, /执行新版合成任务/);
  assert.match(call.prompt, /禁止创建\/派发其他代理/);
  assert.equal('task' in call, false);
  assert.equal('session' in call, false);
  assert.equal(h.w().state.allocations[0].status, 'completed');
  assert.equal('sessionId' in h.w().state.allocations[0], false);
});
test('calls[] adapter preserves default model inheritance when no selection was requested', async () => {
  const h = harness();
  await h.start('multi 合成继承');

  await releaseSlice(h);
  const result = await h.invoke('coding_delegate', {
    revision: h.w().state.revision,
    tool: 'subagent',
    evidence: [h.userRef()],
    jobs: [{ role: 'Primary Output', agent: 'worker', task: 'inherit', paths: [] }],
  });
  assert.equal(result.isError, false);
  const [call] = h.calls.find((c) => c.name === 'subagent').input.calls;
  assert.equal('model' in call, false);
  assert.equal('thinking' in call, false);
  assert.equal('session' in call, false);
});
test('calls[] preflight rejects unsupported model/thinking before any reservation or execution', async () => {
  for (const missing of ['model', 'thinking', 'unsupported-medium']) {
    const h = harness();
    await h.start('multi 2 合成新版前检');

    await releaseSlice(h);
    const schema = structuredClone(callsSchema),
      fields = schema.properties.calls.items.properties;
    if (missing === 'unsupported-medium') fields.thinking.enum = ['low'];
    else delete fields[missing];
    h.raw.get('subagent').parameters = schema;
    const result = await h.invoke('coding_delegate', {
      revision: h.w().state.revision,
      tool: 'subagent',
      evidence: [h.userRef()],
      jobs: [
        { role: 'Primary Output', agent: 'worker', task: 'valid first', paths: [] },
        {
          role: 'Context Bootstrap/Refresh',
          agent: 'scout',
          task: 'unsupported later selection',
          paths: [],
          model: 'openai/gpt-6-luna:medium',
          modelReason: 'bounded',
        },
      ],
    });
    assert.equal(result.isError, true);
    assert.equal(h.w().state.allocations.length, 0);
    assert.equal(h.calls.filter((c) => c.name === 'subagent').length, 0);
  }
});
test('calls[] jobs remain separate host calls; child failure retains occupied budgets', async () => {
  const h = harness();
  await h.start('multi 2 合成新版失败');

  await releaseSlice(h);
  h.raw.get('subagent').execute = async (_id, input) => ({
    ...body('实际失败与部分结果'),
    isError: input.calls[0].agent === 'scout',
  });
  const result = await h.invoke('coding_delegate', {
    revision: h.w().state.revision,
    tool: 'subagent',
    evidence: [h.userRef()],
    jobs: [
      { role: 'Primary Output', agent: 'worker', task: 'first', paths: [] },
      { role: 'Context Bootstrap/Refresh', agent: 'scout', task: 'second', paths: [] },
    ],
  });
  assert.equal(result.isError, true);
  assert.equal(h.calls.filter((c) => c.name === 'subagent').length, 2);
  assert.deepEqual(
    h.w().state.allocations.map((a) => a.status),
    ['completed', 'failed'],
  );
  assert.equal(h.w().state.allocations.length, 2);
});
test('calls[] Schema cannot bypass direct-call and coding_run delegation guards', async () => {
  const h = harness();
  await h.start('multi 合成旁路');

  await releaseSlice(h);
  const input = { calls: [{ agent: 'worker', prompt: 'must not run' }] };
  assert.equal((await h.invoke('subagent', input)).isError, true);
  assert.equal((await h.run('subagent', 'read', input)).isError, true);
  assert.equal(h.calls.filter((c) => c.name === 'subagent').length, 0);
  assert.equal(h.w().state.allocations.length, 0);
});
test('calls[] recognition rejects unsupported required fields and incompatible array/context shapes', () => {
  assert.equal(compatibleSubagent(callsSchema), true);
  for (const change of [
    (s) => s.required.push('unsupported'),
    (s) => s.properties.calls.items.required.push('session'),
    (s) => s.properties.calls.items.required.push('unsupported'),
    (s) => {
      s.properties.calls.type = 'string';
    },
    (s) => {
      s.properties.calls.minItems = 2;
    },
    (s) => {
      s.properties.calls.maxItems = 0;
    },
    (s) => {
      s.properties.calls.items.properties.prompt.type = 'number';
    },
    (s) => {
      delete s.properties.calls.items.properties.cwd;
    },
    (s) => {
      delete s.properties.calls.items.properties.initialContext;
    },
    (s) => {
      s.properties.calls.items.properties.initialContext.enum = ['parent'];
    },
  ]) {
    const schema = structuredClone(callsSchema);
    change(schema);
    assert.equal(compatibleSubagent(schema), false, JSON.stringify(schema));
  }
});
test('calls[] incompatible required fields fail before reserving even when a prior job is valid', async () => {
  const h = harness();
  await h.start('multi 2 合成未知必需字段');

  await releaseSlice(h);
  const schema = structuredClone(callsSchema);
  schema.properties.calls.items.required.push('session');
  h.raw.get('subagent').parameters = schema;
  const result = await h.invoke('coding_delegate', {
    revision: h.w().state.revision,
    tool: 'subagent',
    evidence: [h.userRef()],
    jobs: [
      { role: 'Primary Output', agent: 'worker', task: 'first', paths: [] },
      { role: 'Context Bootstrap/Refresh', agent: 'scout', task: 'second', paths: [] },
    ],
  });
  assert.equal(result.isError, true);
  assert.equal(h.w().state.allocations.length, 0);
  assert.equal(h.calls.filter((c) => c.name === 'subagent').length, 0);
});
test('calls[] still rejects single mode, Git roles, duplicate roles and conflicting paths', async () => {
  const primary = { role: 'Primary Output', agent: 'worker', task: 'first', paths: [] };
  const scenarios = [
    { name: 'single', start: 'single 合成禁止委派', jobs: [primary] },
    {
      name: 'git',
      start: 'multi 2 合成新版门禁',
      jobs: [{ ...primary, role: 'Documentation/Comments & Git Operations' }],
    },
    {
      name: 'duplicate',
      start: 'multi 2 合成新版门禁',
      jobs: [primary, { ...primary, task: 'duplicate' }],
    },
    {
      name: 'paths',
      start: 'multi 2 合成新版门禁',
      jobs: [{ ...primary, paths: ['synthetic.ts', 'synthetic.ts'] }],
    },
  ];
  for (const { name, start, jobs } of scenarios) {
    const h = harness();
    await h.start(start);

    await releaseSlice(h);

    const result = await h.invoke('coding_delegate', {
      revision: h.w().state.revision,
      tool: 'subagent',
      evidence: [h.userRef()],
      jobs,
    });

    assert.equal(result.isError, true, name);
    assert.equal(h.w().state.allocations.length, 0, name);
    assert.ok(!h.calls.some((call) => call.name === 'subagent'), name);
  }
});
test('calls[] preserves the independent read-only verification boundary and current epoch evidence', async () => {
  const h = harness();
  await h.start('multi 合成新版验证');

  const job = { role: 'Change Verification', agent: 'reviewer', task: 'verify actual evidence', paths: [] };
  const blocked = await h.invoke('coding_delegate', {
    revision: h.w().state.revision,
    tool: 'subagent',
    evidence: [h.userRef()],
    jobs: [{ ...job, paths: ['synthetic.ts'] }],
  });
  assert.equal(blocked.isError, true);
  assert.equal(h.w().state.allocations.length, 0);
  const result = await h.invoke('coding_delegate', {
    revision: h.w().state.revision,
    tool: 'subagent',
    evidence: [h.userRef()],
    jobs: [job],
  });
  assert.equal(result.isError, false);
  assert.match(h.calls.find((c) => c.name === 'subagent').input.calls[0].prompt, /只读，不准写项目文件/);
  const evidence = h.w().state.observations.find((o) => o.effect === 'check');
  assert.ok(evidence?.ok);
  assert.deepEqual(evidence.epoch, h.w().state.epoch);
});
test('a same-named tool with a legacy schema is rejected before execution or reservation', async () => {
  const h = harness();
  await h.start('multi 合成仅含旧参数的工具');
  await releaseSlice(h);
  const legacySchema = {
    type: 'object',
    properties: {
      agent: { type: 'string' },
      task: { type: 'string' },
      cwd: { type: 'string' },
    },
    required: ['agent', 'task'],
  };
  h.raw.get('subagent').parameters = legacySchema;
  assert.equal(compatibleSubagent(legacySchema), false);
  assert.equal(
    (await h.invoke('subagent', { agent: 'worker', task: 'forbidden', cwd: process.cwd() })).isError,
    true,
  );
  const args = {
    revision: h.w().state.revision,
    tool: 'subagent',
    evidence: [h.userRef()],
    jobs: [{ role: 'Primary Output', agent: 'worker', task: 'test', paths: [] }],
  };
  assert.equal((await h.invoke('coding_delegate', args)).isError, true);
  assert.equal(h.w().state.allocations.length, 0);
  assert.equal((await h.run('subagent', 'read')).isError, true);
  assert.equal(h.calls.filter((call) => call.name === 'subagent').length, 0);
});
test('parallel delegate preflight rejects budget overflow and conflicting writes before any task', async () => {
  const h = harness();
  await h.start('multi 合成实现任务');

  await releaseSlice(h);
  const jobs = [
    { role: 'Primary Output', agent: 'worker', task: 'test', paths: [] },
    { role: 'Context Bootstrap/Refresh', agent: 'worker', task: 'test', paths: [] },
  ];
  const result = await h.invoke('coding_delegate', {
    revision: h.w().state.revision,
    tool: 'subagent',
    evidence: [h.userRef()],
    jobs,
  });
  assert.equal(result.isError, true);
  assert.equal(h.w().state.allocations.length, 0);
  assert.equal(h.calls.filter((c) => c.name === 'subagent').length, 0);
});
