#!/usr/bin/env node
import assert from 'node:assert/strict';
import { lstatSync, readFileSync, realpathSync, writeFileSync } from 'node:fs';
import { dirname, join, sep } from 'node:path';
import {
  documentLinks,
  HOOK_IDS,
  loadCatalog,
  resolveDocumentLink,
} from '../extensions/coding-workflow/catalog.ts';
import { makeState, Workflow } from '../extensions/coding-workflow/engine.ts';
import { MAX_CONTEXT, renderContext } from '../extensions/coding-workflow/rules/prompt.ts';
import {
  collectSourceCoverage,
  coverageYaml,
  headingAnchors,
  readHookSources,
  SKILL_ROOT,
  validateMarkdownLinks,
} from './pi-hook-validation.mjs';

function checkExportedRule(catalog, path) {
  const markdown = readFileSync(join(SKILL_ROOT, path), 'utf8');
  const linkCount = validateMarkdownLinks(SKILL_ROOT, path, markdown);
  const anchors = headingAnchors(markdown);
  for (const fragment of catalog.references.documentForPath(path).fragments) {
    if (fragment.kind === 'section') {
      assert.ok(anchors.has(fragment.anchor), `${path}: 导出缺少片段 ${fragment.id} 的标题锚点`);
    }
  }
  if (!path.startsWith('references/')) return linkCount;

  const hookDirectory = join(SKILL_ROOT, 'hooks') + sep;
  for (const target of documentLinks(markdown)) {
    const link = resolveDocumentLink(SKILL_ROOT, path, target);
    assert.ok(!link?.path.startsWith(hookDirectory), `${path}: 底层规则不能反向依赖 Hook ${target}`);
  }
  return linkCount;
}

function checkCoverage(catalog, rows, writeRequested) {
  const coveragePath = join(catalog.root, 'hooks/SOURCE_COVERAGE.yaml');
  const expected = coverageYaml(rows);
  const directory = dirname(coveragePath);
  assert.equal(realpathSync(directory), directory, '来源对照目录不得经过符号链接');
  assert.ok(!lstatSync(coveragePath, { throwIfNoEntry: false })?.isSymbolicLink(), '来源对照不得是符号链接');
  if (writeRequested) writeFileSync(coveragePath, expected);
  assert.equal(
    readFileSync(coveragePath, 'utf8'),
    expected,
    '来源对照表过期，请运行 node scripts/check-pi-hooks.mjs --write-coverage 并审阅变化',
  );
}

function measureModeContexts(catalog, mode) {
  const samples = [];
  for (const capabilityChanged of [false, true]) {
    for (const status of ['active', 'paused']) {
      const childCount = mode === 'single' ? 0 : 1;
      const state = makeState(
        catalog,
        { sessionId: 'hook-check', cwd: process.cwd() },
        { mode, childCount, task: '有界合成任务' },
      );
      Object.assign(state, { capabilityChanged, status });
      samples.push({
        isDefault: !capabilityChanged && status === 'active',
        size: renderContext(new Workflow(catalog, state)).length,
      });
    }
  }
  return samples;
}

function measureContexts(catalog) {
  const samples = [];
  for (const mode of ['single', 'multi']) {
    samples.push(...measureModeContexts(catalog, mode));
  }
  const defaults = samples.filter((sample) => sample.isDefault);
  return {
    contexts: samples.length,
    maxDefaultContextCharacters: Math.max(...defaults.map((sample) => sample.size)),
    maxConditionalContextCharacters: Math.max(...samples.map((sample) => sample.size)),
  };
}

const catalog = loadCatalog();
const hooks = readHookSources(SKILL_ROOT);
let checkedLocalLinks = 0;
for (const id of HOOK_IDS) {
  checkedLocalLinks += validateMarkdownLinks(SKILL_ROOT, `hooks/${id}.md`, hooks[id]);
}
for (const path of catalog.references.documentPaths()) {
  if (!path.startsWith('hooks/')) checkedLocalLinks += checkExportedRule(catalog, path);
}

const rows = collectSourceCoverage(SKILL_ROOT, hooks);
checkCoverage(catalog, rows, process.argv.includes('--write-coverage'));
for (const name of ['README', 'SOURCE_COVERAGE']) {
  const path = `hooks/${name}.md`;
  checkedLocalLinks += validateMarkdownLinks(SKILL_ROOT, path, readFileSync(join(SKILL_ROOT, path), 'utf8'));
}
const contextSizes = measureContexts(catalog);
assert.equal(new Set(rows.map((row) => row.path)).size, rows.length);
const counts = Object.fromEntries(
  ['rule', 'navigation', 'reference'].map((kind) => [kind, rows.filter((row) => row.kind === kind).length]),
);
console.log(
  JSON.stringify(
    {
      hooks: HOOK_IDS.length,
      sources: rows.length,
      counts,
      explicitArticleCoverage: rows.filter((row) => row.kind !== 'navigation' && row.hooks.length).length,
      checkedLocalLinks,
      ...contextSizes,
      contextLimit: MAX_CONTEXT,
      catalogHash: catalog.digest,
      note: '全文执行条款注入；逐篇来源表驻盘。链接、锚点和显式归属检查不证明所有条款语义等价、权限真实或端到端验收。外部URL未联网验证。',
    },
    null,
    2,
  ),
);
