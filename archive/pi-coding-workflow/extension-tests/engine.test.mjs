import assert from 'node:assert/strict';
import { test } from 'node:test';
import { exactPath } from '../extensions/coding-workflow/engine.ts';
import { harness, releaseSlice } from './pi-runtime-fixture.mjs';

test('Git preflight uses actual check receipts and rejects stale content without a phase cursor', async () => {
  const host = harness();
  await host.start();
  await releaseSlice(host, { mutations: ['content', 'git'] });
  const git = (ids) => host.run('bash', 'git', {}, ids);
  assert.equal((await git([host.userRef()])).isError, true);
  assert.equal((await host.run('bash', 'git')).isError, true);

  const firstCheck = await host.run('bash', 'check');
  assert.equal((await host.invoke('write', { path: 'synthetic.ts' })).isError, false);
  assert.equal((await host.run('bash', 'git')).isError, true);
  assert.equal((await git([firstCheck.toolCall.id])).isError, true);

  const freshCheck = await host.run('bash', 'check');
  assert.equal((await git([freshCheck.toolCall.id])).isError, false);
  assert.equal(host.w().state.epoch.git, 1);
  assert.equal((await git([freshCheck.toolCall.id])).isError, false);
  assert.equal(host.w().state.epoch.git, 2);
  await host.emit('input', { source: 'rpc', text: 'new scope' });
  await releaseSlice(host, { mutations: ['git'] });
  assert.equal((await git([freshCheck.toolCall.id])).isError, true);
});

test('settled turns revoke write scope without a finish report and retain pending effects', async () => {
  const host = harness();
  await host.start();
  const saved = host.entries.length;
  await releaseSlice(host);
  await host.invoke('read', { path: 'synthetic.ts' });
  await host.emit('agent_settled', { aborted: false });
  assert.equal(host.w().state.status, 'active');
  assert.equal(host.w().state.slice, undefined);
  assert.equal((await host.invoke('write', { path: 'synthetic.ts' })).isError, true);
  assert.equal(host.entries.length, saved);
  const snapshot = host.entries.at(-1).data.state;
  assert.equal(snapshot.version, 3);
  for (const key of ['task', 'status', 'slice', 'observations', 'epoch', 'revision']) {
    assert.equal(key in snapshot, false, key);
  }

  host.w().state.inFlight.push('unresolved');
  await host.emit('agent_settled', { aborted: false });
  assert.equal(host.w().state.status, 'paused');
  assert.deepEqual(host.entries.at(-1).data.state.inFlight, ['unresolved']);
});

test('legacy snapshots retain allocations and pending effects but drop the old cursor and write scope', async () => {
  const host = harness();
  await host.start('multi 合成任务');
  const entry = host.entries.at(-1).data;
  const snapshot = entry.state;
  entry.answers = { mode: snapshot.mode, count: snapshot.childCount, audit: snapshot.audit };
  Object.assign(snapshot, {
    version: 1,
    catalogHash: 'previous-rules',
    phase: 'execution',
    step: 4,
    inFlight: ['legacy-call'],
    allocations: [{ id: 'allocation', callId: 'legacy-call', role: 'Primary Output', status: 'running' }],
    slice: { paths: ['old.ts'] },
  });
  const restored = harness({ entries: host.entries });
  await restored.emit('session_start', { reason: 'resume' });
  await restored.invoke('read', { path: 'synthetic.ts' });
  assert.equal(restored.entries.at(-1).data.state.version, 3);
  assert.match(restored.w().state.recoveryHint, /execution\/4/);
  assert.equal('phase' in restored.w().state, false);
  assert.equal(restored.w().state.slice, undefined);
  assert.equal(restored.w().state.allocations[0].status, 'uncertain');
  assert.deepEqual(restored.w().state.inFlight, ['legacy-call']);
  assert.equal(restored.w().state.status, 'paused');
});

test('exact path guard rejects directories, traversal, metadata and globs', () => {
  for (const path of ['/root/file', 'dir/../file', './a', '.git/config', 'dir/', 'dir/*', '@alias']) {
    assert.equal(exactPath(path), false, path);
  }
  assert.equal(exactPath('dir/file.ts'), true);
});
