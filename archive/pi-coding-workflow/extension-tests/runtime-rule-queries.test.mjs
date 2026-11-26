import assert from 'node:assert/strict';
import { cpSync, existsSync, mkdtempSync, realpathSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { test } from 'node:test';
import { documentLinks, loadCatalog } from '../extensions/coding-workflow/catalog.ts';
import { catalog, harness } from './pi-runtime-fixture.mjs';

const routeHooks = [
  'entry',
  'session',
  'planning',
  'execution',
  'delegation',
  'verification',
  'documentation',
  'delivery',
];

async function readRule(host, request = {}) {
  const response = await host.invoke('coding_checkpoint', { action: 'rules', ...request });
  const content = response.result.content[0].text;
  assert.equal(response.isError, false, content);
  return JSON.parse(content);
}

async function verifyNavigation(host, before) {
  const navigation = [
    ['routes', ['coding-rule:coding-single-agent', 'coding-rule:coding-multi-agent']],
    ['section-01', routeHooks.map((id) => 'coding-rule:hook-' + id)],
  ];
  for (const [fragment, links] of navigation) {
    const document = 'layer-04-readme';
    const result = await readRule(host, { document, fragment });
    assert.equal(result.document, document);
    assert.equal(result.fragment, fragment);
    assert.deepEqual(documentLinks(result.content), links);
    assert.deepEqual(structuredClone(host.w().state), before.state);
    assert.deepEqual(host.entries, before.entries);
  }
}

async function verifyCurrentRule(host, { owner, checkpoint }) {
  const index = await readRule(host, { document: owner });
  assert.equal(index.document, owner);
  assert.match(index.content, /执行要求/);
  assert.ok(
    index.fragments.some(
      (item) => item.id === checkpoint && item.kind === 'checkpoint' && !('content' in item),
    ),
  );
  const rule = await readRule(host, { document: owner, fragment: checkpoint });
  assert.equal(rule.fragment, checkpoint);
  assert.ok(rule.content.length);
}

async function verifySharedRules(host, mode) {
  const returns = await readRule(host, { document: `coding-${mode}-agent`, fragment: 'returns' });
  assert.match(returns.content, /原挂起.*子步骤/);
  const creation = await readRule(host, { document: 'delegation-child-creation', fragment: 'rules' });
  assert.match(creation.content, /coding-rule:runtime-provider-support#subagent-endpoint/);
  const endpoint = await readRule(host, {
    document: 'runtime-provider-support',
    fragment: 'subagent-endpoint',
  });
  assert.match(endpoint.content, /端点/);
}

test('both routes and rule queries work with the YAML sources alone', async (t) => {
  const root = realpathSync(mkdtempSync(join(tmpdir(), 'pi-runtime-data-')));
  t.after(() => rmSync(root, { recursive: true, force: true }));
  cpSync(catalog.root, root, { recursive: true });
  assert.ok(!existsSync(join(root, 'coding-workflows', 'README.md')));
  const installed = loadCatalog(root);
  assert.equal(installed.digest, catalog.digest);

  const scenarios = [
    {
      mode: 'single',
      route: 'SM04',
      owner: 'hook-execution',
      checkpoint: 'SE03',
    },
    {
      mode: 'multi',
      route: 'MM04',
      owner: 'hook-delegation',
      checkpoint: 'DE04',
    },
  ];
  for (const scenario of scenarios) {
    const { mode, route, owner } = scenario;
    const host = harness({ catalog: installed });
    await host.start(`${mode} 合成规则请求`);
    const [message] = (await host.emit('context', { messages: [] })).messages;
    assert.match(message.content, new RegExp(route));
    assert.match(message.content, new RegExp(owner));
    const before = { state: structuredClone(host.w().state), entries: structuredClone(host.entries) };

    await verifyNavigation(host, before);
    await verifyCurrentRule(host, scenario);
    await verifySharedRules(host, mode);
    const invalid = await host.invoke('coding_checkpoint', {
      action: 'rules',
      document: '../references/unknown.md',
    });
    assert.equal(invalid.isError, true);
    assert.deepEqual(structuredClone(host.w().state), before.state);
    assert.deepEqual(host.entries, before.entries);
  }
});
