import assert from 'node:assert/strict';
import { test } from 'node:test';
import { mkdtempSync, readFileSync, rmSync, symlinkSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { MAX_CONTEXT, scopedPath } from '../extensions/coding-workflow/runtime.ts';
import { releaseSlice, body, harness } from './pi-runtime-fixture.mjs';

test('package declares one extension and excludes local Serena metadata by a narrow files allowlist', () => {
  const manifest = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'));
  assert.deepEqual(manifest.pi.extensions, ['./extensions/coding-workflow/index.ts']);
  assert.deepEqual(manifest.files, [
    'CHANGELOG/CHANGELOG.md',
    'CHANGELOG/CODE_QUALITY.md',
    'extensions/coding-workflow/**/*.ts',
    'docs/rules',
    'docs/project',
    'docs/skill',
    'agents/*.md',
    'integrations/pi-subagent/*',
    'README.md',
  ]);
  assert.equal(manifest.peerDependencies.typebox, '*');
});

test('context injects only relevant hooks once and preserves unrelated extension messages', async () => {
  const h = harness();
  await h.start();
  const other = { role: 'custom', customType: 'other-extension', content: 'keep' };
  const first = await h.emit('context', { messages: [other] });
  const second = await h.emit('context', { messages: first.messages });
  assert.equal(second.messages.length, 2);
  assert.equal(second.messages[0], other);
  assert.match(second.messages[1].content, /Hook:foundation/);
  assert.doesNotMatch(second.messages[1].content, /Hook:materialization/);
  assert.ok(second.messages[1].content.length < MAX_CONTEXT);
});
test('unknown direct shell and lying readOnlyHint do not pass the wrapper gate', async () => {
  const h = harness();
  await h.start();
  assert.equal((await h.invoke('bash', {})).isError, true);
  h.raw.set('opaque_mcp', {
    parameters: {},
    annotations: { readOnlyHint: true },
    execute: async () => body('not a security proof'),
  });
  assert.equal((await h.invoke('opaque_mcp', {})).isError, true);
});
test('coding_run calls actual exposed target through host hooks and captures real evidence', async () => {
  const h = harness();
  await h.start();
  const out = await h.run();
  assert.equal(out.isError, false);
  assert.ok(h.calls.some((c) => c.name === 'bash' && c.parentToolCallId));
  assert.ok(h.w().state.observations.some((o) => o.tool === 'bash' && o.ok));
  assert.equal(h.w().state.inFlight.length, 0);
});
test('wrapper cannot call hidden/unknown/internal/recursive or subagent tools', async () => {
  const h = harness();
  await h.start();
  h.raw.set('hidden', { hidden: true, parameters: {}, execute: async () => body('must not run') });
  for (const target of ['hidden', 'missing', 'coding_run', 'coding_checkpoint', 'subagent'])
    assert.equal((await h.run(target)).isError, true, target);
  assert.equal(h.w().state.allocations.length, 0);
});
test('opaque content mutation is blocked before Slice release', async () => {
  const h = harness();
  await h.start();
  assert.equal((await h.run('bash', 'content')).isError, true);
  assert.equal(h.calls.filter((c) => c.name === 'bash').length, 0);
});
test('built-in writes enforce the exact released path and invalidate the correct epoch', async () => {
  const h = harness();
  await h.start();
  assert.equal((await h.invoke('write', { path: 'synthetic.ts' })).isError, true);

  await releaseSlice(h);
  assert.equal((await h.invoke('write', { path: 'other.ts' })).isError, true);
  assert.equal((await h.invoke('write', { path: 'synthetic.ts' })).isError, false);
  assert.equal(h.w().state.epoch.content, 1);
  assert.deepEqual(h.w().state.inFlight, []);
});
test('failed writes may partially mutate and invalidate; blocked calls do not', async () => {
  const h = harness();
  await h.start();

  await releaseSlice(h);
  h.raw.get('write').execute = async () => {
    throw new Error('partial write failure');
  };
  assert.equal((await h.invoke('write', { path: 'synthetic.ts' })).isError, true);
  assert.equal(h.w().state.epoch.content, 1);
  assert.equal((await h.invoke('write', { path: 'other.ts' })).isError, true);
  assert.equal(h.w().state.epoch.content, 1);
  h.pi.on('tool_call', (event) =>
    event.toolName === 'bash' ? { block: true, reason: 'synthetic host denial before execute' } : undefined,
  );
  assert.equal((await h.run('bash', 'content')).isError, true);
  assert.equal(h.w().state.epoch.content, 1);
});
test('nested writes cannot bypass exact-path gates inside a read-classified orchestrator', async () => {
  const h = harness();
  await h.start();

  await releaseSlice(h);
  h.raw.set('orchestrator', {
    parameters: {},
    execute: async (_id, _p, _s, _u, ctx) => (await ctx.executeTool('write', { path: 'escape.ts' })).result,
  });
  await h.run('orchestrator');
  assert.equal(h.w().state.epoch.content, 0);
  assert.equal(h.calls.filter((c) => c.name === 'write').length, 0);
});

test('user steering rechecks write scope, compaction keeps it, and unknown effects pause', async () => {
  for (const [event, payload, status, keepsSlice] of [
    ['agent_settled', { aborted: true }, 'paused', false],
    ['input', { source: 'rpc', text: 'new requirement' }, 'active', false],
    ['session_compact', {}, 'active', true],
    ['user_bash', {}, 'paused', false],
  ]) {
    const h = harness();
    await h.start();

    await releaseSlice(h);
    await h.emit(event, payload);
    assert.equal(h.w().state.status, status, event);
    assert.equal(Boolean(h.w().state.slice), keepsSlice, event);
    if (status === 'active' && !keepsSlice) await releaseSlice(h);
  }
});
test('normal settlement leaves the agent in charge and requests no continuation', async () => {
  const h = harness();
  await h.start();
  assert.equal(
    await h.emit('agent_before_settle', { outcome: 'completed', context: { canContinue: true } }),
    undefined,
  );
  assert.equal(h.w().state.status, 'active');
});
test('restore uses active branch session facts but never refunds abandoned-branch child allocation', async () => {
  const h = harness();
  await h.start('multi 合成任务');
  const initial = structuredClone(h.entries);

  await releaseSlice(h);
  await h.invoke('coding_delegate', {
    revision: h.w().state.revision,
    tool: 'subagent',
    evidence: [h.userRef()],
    jobs: [{ role: 'Primary Output', agent: 'worker', task: 'one shot', paths: [] }],
  });
  h.setBranch(initial);
  await h.emit('session_tree');
  assert.equal('phase' in h.w().state, false);
  assert.equal(h.w().state.status, 'paused');
  assert.equal(h.w().state.allocations.length, 1);
});
test('fork/new Session never inherits parent workflow identity or progress', async () => {
  const h = harness();
  await h.start();
  h.setSessionId('forked-session');
  await h.emit('session_start', { reason: 'fork' });
  assert.equal(h.w(), undefined);
  assert.equal(h.isEnabled(), false);
});
test('corrupt latest snapshot is fail-closed and cannot be reset by another start command', async () => {
  const h = harness();
  await h.start();
  h.entries.at(-1).data.state.version = 99;
  await h.emit('session_start', { reason: 'reload' });
  assert.match(h.getRestoreError(), /快照版本/);
  assert.equal((await h.invoke('write', { path: 'anything.ts' })).isError, true);
  await h.commands.get('coding').handler('single 不能重置绕过', h.ctx);
  assert.equal(h.w(), undefined);
});
test('unresolved effects survive restoration and block resume until actual readback', async () => {
  const h = harness();
  await h.start();
  h.w().state.inFlight.push('unknown-op');
  await h.emit('agent_settled', { aborted: true });
  const pendingBranch = structuredClone(h.entries);
  await h.emit('session_start', { reason: 'reload' });
  assert.ok(h.w().state.inFlight.includes('unknown-op'));
  const resume = await h.invoke('coding_checkpoint', {
    action: 'resume',
    revision: h.w().state.revision,
    evidence: ['obsolete-receipt'],
  });
  assert.equal(resume.isError, true);
  const read = await h.invoke('read', { path: 'synthetic.ts' });
  assert.equal(
    (
      await h.invoke('coding_checkpoint', {
        action: 'resolve_effect',
        revision: h.w().state.revision,
        callId: 'unknown-op',
        evidence: [read.toolCall.id],
      })
    ).isError,
    false,
  );
  h.setBranch(pendingBranch);
  await h.emit('session_tree');
  assert.deepEqual(h.w().state.inFlight, []);
});
test('explicit volatile flag avoids appendEntry; no global configuration is modified', async () => {
  const h = harness({ flags: { 'coding-volatile': true } });
  await h.start();
  await h.run();
  assert.equal(h.entries.length, 0);
});
test('large actual result is paginated without rerunning the target task', async () => {
  const h = harness();
  await h.start();
  h.raw.get('bash').execute = async () => body('x'.repeat(70000));
  const outcome = await h.run();
  const record = JSON.parse(outcome.result.content[0].text);
  assert.equal(record.nextOffset, 24000);
  const page = await h.invoke('coding_checkpoint', {
    action: 'result',
    resultId: record.callId,
    offset: record.nextOffset,
  });
  assert.equal(page.isError, false);
  assert.equal(h.calls.filter((c) => c.name === 'bash').length, 1);
});
test('host-confirmed blocked delegate does not consume an unbound reservation after reload', async () => {
  const h = harness();
  await h.start('multi 合成任务');

  await releaseSlice(h);
  h.pi.on('tool_call', (event) =>
    event.toolName === 'subagent'
      ? { block: true, reason: 'synthetic host denial before execute' }
      : undefined,
  );
  const outcome = await h.invoke('coding_delegate', {
    revision: h.w().state.revision,
    tool: 'subagent',
    evidence: [h.userRef()],
    jobs: [{ role: 'Primary Output', agent: 'worker', task: 'test', paths: [] }],
  });
  assert.equal(outcome.isError, true);
  assert.equal(h.w().state.allocations.length, 0);
  await h.emit('session_start', { reason: 'reload' });
  assert.equal(h.w().state.allocations.length, 0);
  assert.equal(h.w().state.childCount, 1);
});
test('volatile tree navigation retains current budget and does not wipe live state', async () => {
  const h = harness({ flags: { 'coding-volatile': true } });
  await h.start('multi 合成任务');

  await releaseSlice(h);
  await h.invoke('coding_delegate', {
    revision: h.w().state.revision,
    tool: 'subagent',
    evidence: [h.userRef()],
    jobs: [{ role: 'Primary Output', agent: 'worker', task: 'test', paths: [] }],
  });
  await h.emit('session_tree');
  assert.equal(h.w().state.allocations.length, 1);
  assert.equal(h.w().state.status, 'paused');
  assert.equal(h.entries.length, 0);
});
test('status observation pagination does not return the entire state/report history', async () => {
  const h = harness();
  await h.start();
  for (let i = 0; i < 50; i++) h.w().observe({ id: `r-${i}`, tool: 'read', effect: 'read', ok: true });
  const result = await h.invoke('coding_checkpoint', { action: 'status', offset: 0 });
  const value = JSON.parse(result.result.content[0].text);
  assert.equal(value.observations.length, 24);
  assert.equal(value.nextObservationsOffset, 24);
  assert.equal('reports' in value, false);
});

test('scope checks reject an existing symlink to outside the project', () => {
  const root = mkdtempSync(join(tmpdir(), 'coding-paths-'));
  const outside = mkdtempSync(join(tmpdir(), 'coding-outside-'));
  try {
    symlinkSync(outside, join(root, 'escape'));
    writeFileSync(join(root, 'safe.ts'), 'test');
    assert.equal(scopedPath(root, 'safe.ts'), 'safe.ts');
    assert.throws(() => scopedPath(root, 'escape/file.ts'), /符号链接/);
    symlinkSync(root, join(root, 'alias'));
    assert.equal(scopedPath(root, 'alias/safe.ts'), 'safe.ts');
  } finally {
    rmSync(root, { recursive: true, force: true });
    rmSync(outside, { recursive: true, force: true });
  }
});
