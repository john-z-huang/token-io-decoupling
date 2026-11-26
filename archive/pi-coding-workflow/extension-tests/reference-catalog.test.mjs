import assert from 'node:assert/strict';
import fs from 'node:fs';
import { syncBuiltinESMExports } from 'node:module';
import { join, sep } from 'node:path';
import { test } from 'node:test';
import { loadCatalog } from '../extensions/coding-workflow/catalog.ts';
import { makeState, Workflow } from '../extensions/coding-workflow/engine.ts';
import { renderContext } from '../extensions/coding-workflow/runtime.ts';
import { SKILL_ROOT } from '../scripts/pi-hook-validation.mjs';

function interceptReads(t, observe) {
  const read = fs.readFileSync;
  t.mock.method(fs, 'readFileSync', (path, ...args) => observe(path, read(path, ...args)));
  syncBuiltinESMExports();
  t.after(() => {
    t.mock.restoreAll();
    syncBuiltinESMExports();
  });
}

function patchSource(t, { file, before, after }) {
  interceptReads(t, (path, content) => {
    if (typeof path !== 'string' || !path.endsWith(file)) return content;
    return Buffer.from(content.toString('utf8').replace(before, after));
  });
}

function syntheticWorkflow(catalog, mode = 'single') {
  return new Workflow(
    catalog,
    makeState(
      catalog,
      { sessionId: 'dsl-test', cwd: process.cwd() },
      { mode, childCount: mode === 'single' ? 0 : 1, task: '合成任务' },
    ),
  );
}

function relativeReads(root, files) {
  const prefix = root + sep;
  return files
    .filter((file) => file.startsWith(prefix))
    .map((file) => file.slice(prefix.length))
    .sort();
}

test('context loads the selected YAML route and triggered contracts without generated Skill', (t) => {
  const files = [];
  interceptReads(t, (path, content) => {
    if (typeof path === 'string') files.push(path);
    return content;
  });
  const catalog = loadCatalog();
  files.length = 0;
  const context = renderContext(syntheticWorkflow(catalog, 'multi'));
  assert.match(context, /MM01[\s\S]+MM07/);
  assert.deepEqual(relativeReads(catalog.root, files), [
    'coding-workflows/coding-multi-agent.yaml',
    'hooks/foundation.yaml',
  ]);
  assert.ok(files.every((file) => !file.startsWith(SKILL_ROOT + sep)));
});

test('unknown YAML activation is rejected', (t) => {
  patchSource(t, { file: 'hooks/advisory.yaml', before: '[advice_requested]', after: '[unknown_signal]' });
  assert.throws(() => loadCatalog(), /activate_on/);
});

test('additional Hook activation is read from YAML', (t) => {
  patchSource(t, {
    file: 'hooks/advisory.yaml',
    before: '[advice_requested]',
    after: '[capability_changed]',
  });
  const workflow = syntheticWorkflow(loadCatalog());
  workflow.state.capabilityChanged = true;
  assert.ok(renderContext(workflow).includes('[Hook:advisory]'));
});

test('a changed YAML source fails the digest check before its triggered Hook is used', (t) => {
  const workflow = syntheticWorkflow(loadCatalog());
  interceptReads(t, (path, content) =>
    typeof path === 'string' && path.endsWith(join('hooks', 'entry.yaml'))
      ? Buffer.from('篡改的指令')
      : content,
  );
  workflow.state.capabilityChanged = true;
  assert.throws(() => renderContext(workflow), /Hash 不匹配：hooks\/entry.yaml/);
});
