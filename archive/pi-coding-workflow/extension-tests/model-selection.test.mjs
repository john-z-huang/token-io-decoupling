import assert from 'node:assert/strict';
import { test } from 'node:test';
import { readFileSync } from 'node:fs';
import {
  parseModelSelection,
  validateChildSelection,
} from '../extensions/coding-workflow/model-selection.ts';
import { releaseSlice, harness } from './pi-runtime-fixture.mjs';
const cards = JSON.parse(
  readFileSync(new URL('../integrations/pi-subagent/model-cards.json', import.meta.url), 'utf8'),
);
for (const card of cards.models)
  for (const effort of card.reasoningEffort)
    test(`${card.id}:${effort} is selectable as a configuration request, not identity proof`, () => {
      const level = effort === 'none' ? 'off' : effort,
        value = `openai/${card.id}:${level}`;
      assert.doesNotThrow(() => validateChildSelection(value));
      assert.deepEqual(parseModelSelection(value), { provider: 'openai', id: card.id, thinking: level });
    });
test('known card limits and precise syntax apply without blocking other model identifiers', () => {
  for (const value of [
    'luna',
    'openai/gpt-6-luna',
    'openai/gpt-6-luna:none',
    'openai/gpt-6-luna:minimal',
    'openai/gpt-6.1-sol:off',
    'openai/*:high',
    'https://key@example.invalid/gpt-6-luna:low',
    'openai/../gpt-6-luna:low',
  ])
    assert.throws(() => validateChildSelection(value), value);
  assert.doesNotThrow(() => validateChildSelection('openrouter/openai/gpt-6.1-terra:medium'));
  assert.doesNotThrow(() => validateChildSelection('local/custom:low'));
});
test('all five Chinese profiles remove fixed model and retain Root/role/effect/recursion boundaries', () => {
  for (const name of ['worker', 'reviewer', 'scout', 'planner', 'git-operator']) {
    const text = readFileSync(new URL(`../agents/${name}.md`, import.meta.url), 'utf8');
    assert.match(text, new RegExp(`name: ${name}\\n`));
    assert.doesNotMatch(text.split('---')[1], /^model:/m);
    for (const guard of ['禁止Computer Use', '不创建/派发其他代理', 'Root亲自负责', '未知效果', '不是OS沙箱'])
      assert.ok(text.includes(guard), name + ': ' + guard);
  }
  assert.match(readFileSync(new URL('../agents/planner.md', import.meta.url), 'utf8'), /不是第五种职责/);
  assert.match(
    readFileSync(new URL('../agents/git-operator.md', import.meta.url), 'utf8'),
    /coding_delegate仍拒绝/,
  );
});

for (const model of ['openai/gpt-6.1-sol', 'openai/gpt-6.1-terra', 'openai/gpt-6-luna', 'local/custom'])
  test(`Root model choice is forwarded through actual declared schema: ${model}`, async () => {
    const h = harness();
    await h.start('multi 合成模型选择');

    await releaseSlice(h);
    const selected = `${model}:medium`;
    const result = await h.invoke('coding_delegate', {
      revision: h.w().state.revision,
      tool: 'subagent',
      evidence: [h.userRef()],
      jobs: [
        {
          role: 'Primary Output',
          agent: 'worker',
          task: 'bounded synthetic task',
          paths: [],
          model: selected,
          modelReason: 'Root按本任务的复杂度与可验证性选择，而非按角色固定',
        },
      ],
    });
    assert.equal(result.isError, false);
    const [call] = h.calls.find((c) => c.name === 'subagent').input.calls;
    assert.equal(call.model, model);
    assert.equal(call.thinking, 'medium');
    assert.equal(h.w().state.allocations.length, 1);
  });
test('invalid model or missing Root rationale rejects all jobs before reserving or calling', async () => {
  for (const choice of [
    { model: 'openai/gpt-6.1-sol:off', modelReason: 'bad level' },
    { model: 'openai/*:medium', modelReason: 'not an exact identifier' },
    { model: 'openai/gpt-6-luna:medium' },
    { modelReason: 'no actual selection' },
  ]) {
    const h = harness();
    await h.start('multi 2 合成原子前检');

    await releaseSlice(h);
    const result = await h.invoke('coding_delegate', {
      revision: h.w().state.revision,
      tool: 'subagent',
      evidence: [h.userRef()],
      jobs: [
        {
          role: 'Primary Output',
          agent: 'worker',
          task: 'first valid synthetic',
          paths: [],
          model: 'openai/gpt-6-luna:low',
          modelReason: 'bounded',
        },
        {
          role: 'Context Bootstrap/Refresh',
          agent: 'scout',
          task: 'later invalid synthetic',
          paths: [],
          ...choice,
        },
      ],
    });
    assert.equal(result.isError, true);
    assert.equal(h.w().state.allocations.length, 0);
    assert.equal(h.calls.filter((c) => c.name === 'subagent').length, 0);
  }
});
test('model selection does not enable an unsupported Git role', async () => {
  const h = harness();
  await h.start('multi 合成Git角色');

  await releaseSlice(h);
  const result = await h.invoke('coding_delegate', {
    revision: h.w().state.revision,
    tool: 'subagent',
    evidence: [h.userRef()],
    jobs: [
      {
        role: 'Documentation/Comments & Git Operations',
        agent: 'git-operator',
        task: 'synthetic',
        paths: [],
        model: 'openai/gpt-6.1-sol:high',
        modelReason: 'cannot create missing adapter',
      },
    ],
  });
  assert.equal(result.isError, true);
  assert.equal(h.w().state.allocations.length, 0);
});
