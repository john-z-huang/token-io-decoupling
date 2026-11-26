import assert from 'node:assert/strict';
import { test } from 'node:test';
import {
  existsSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  rmSync,
  symlinkSync,
  writeFileSync,
} from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  documentLinks,
  HOOK_IDS,
  rewriteWorkflowLinks,
  loadCatalog,
  resolveDocumentLink,
  resolveHookLink,
  rewriteDocumentLinks,
} from '../extensions/coding-workflow/catalog.ts';
import { makeState, Workflow } from '../extensions/coding-workflow/engine.ts';
import { MAX_CONTEXT, renderContext, renderHook } from '../extensions/coding-workflow/runtime.ts';
import {
  classifySource,
  collectSourceCoverage,
  coverageYaml,
  headingAnchors,
  readHookSources,
  SKILL_ROOT,
  validateMarkdownLinks,
} from '../scripts/pi-hook-validation.mjs';
const catalog = loadCatalog();
const hookSources = readHookSources(SKILL_ROOT);

function assertInjectedLinks(injected) {
  for (const target of documentLinks(injected)) {
    assert.match(target, /^(?:coding-rule:|file:|https?:|mailto:|\/\/)/i, `unbased injected link: ${target}`);
    if (target.startsWith('file:')) assert.ok(existsSync(fileURLToPath(new URL(target))));
    if (target.startsWith('coding-rule:')) {
      const [id, fragment] = target.slice('coding-rule:'.length).split('#');
      const owner = catalog.references.document(id);
      if (fragment) assert.ok(owner.fragments.some((item) => item.id === fragment));
    }
  }
}

for (const id of HOOK_IDS)
  test(`${id}: complete execution clauses and every portable source link survive injection`, () => {
    const document = `hooks/${id}.md`,
      source = hookSources[id];
    assert.ok(validateMarkdownLinks(SKILL_ROOT, document, source) > 0);
    const notice = `\n\n<!-- 由 docs/rules/hooks/${id}.yaml 生成。请在 DSL 中维护正文。 -->`;
    assert.ok(source.includes(notice));
    const body = source
      .slice(0, source.indexOf('\n## 规则来源\n'))
      .replace(notice, '')
      .replace(/\n## 工作流路线图\n[\s\S]*?(?=\n## (?:输出与落点|退出与阻断)\n)/, '')
      .trimEnd();
    assert.equal(
      rewriteWorkflowLinks(catalog, document, catalog.references.readHook(id)),
      rewriteWorkflowLinks(catalog, document, body),
    );
    const injected = renderHook(catalog, id, 'single');
    let expected = rewriteWorkflowLinks(catalog, document, body);
    const include = {
      entry: [null, 'coding-single-agent', 'mode-boundary'],
      verification: ['verification-epoch', 'verification-epoch', 'actions'],
    }[id];
    if (include) {
      const [marker, sourceId, block] = include;
      const owner = catalog.references.document(sourceId);
      const fragment = rewriteWorkflowLinks(
        catalog,
        owner.path,
        catalog.references.readFragment(owner.id, block),
      );
      expected = marker
        ? expected.replace(`<!-- rule:${marker}#${block} -->`, () => fragment)
        : expected + '\n\n## 当前路线的 Mode 边界\n\n' + fragment;
      assert.ok(injected.includes(fragment));
    }
    assert.equal(injected.slice(injected.indexOf('\n\n') + 2), expected);
    for (const title of ['触发条件', '执行要求', '退出与阻断', '重新核验'])
      assert.ok(injected.includes(`\n## ${title}\n`));
    assert.ok(
      !injected.includes('| 来源 | 本合同落点 |'),
      'only the non-executable provenance table is left on disk',
    );
    assert.ok(!injected.includes('## 有序模块清单'), 'only the current checkpoint is separately read');
    assertInjectedLinks(injected);
  });

test('all substantive articles have explicit per-hook provenance and the checked-in map is current', () => {
  const rows = collectSourceCoverage(SKILL_ROOT);
  assert.ok(rows.length >= 93);
  assert.ok(rows.every((row) => !row.path.endsWith('/INDEX.md')));
  assert.ok(rows.every((row) => !row.path.startsWith('coding-workflows/')));
  assert.equal(rows.filter((row) => row.path.includes('layer-01-') && row.kind === 'rule').length, 41);
  assert.ok(rows.every((row) => row.declaredHooks.length));
  assert.throws(() => classifySource('references/new-policy/rule.md'), /没有 Hook/);
  assert.ok(rows.filter((row) => row.kind === 'rule').every((row) => row.hooks.length));
  assert.equal(readFileSync(join(catalog.root, 'hooks/SOURCE_COVERAGE.yaml'), 'utf8'), coverageYaml(rows));
  for (const name of ['README', 'SOURCE_COVERAGE'])
    validateMarkdownLinks(
      SKILL_ROOT,
      `hooks/${name}.md`,
      readFileSync(join(SKILL_ROOT, `hooks/${name}.md`), 'utf8'),
    );
});

test('removing one unique source citation fails coverage rather than silently assigning by directory', () => {
  const row = collectSourceCoverage(SKILL_ROOT).find((row) => row.kind === 'rule' && row.hooks.length === 1);
  assert.ok(row);
  const id = row.hooks[0];
  const changed = {
    ...hookSources,
    [id]: hookSources[id]
      .split('\n')
      .filter((line) => !line.includes(`](../${row.path})`))
      .join('\n'),
  };
  assert.throws(() => collectSourceCoverage(SKILL_ROOT, changed), /实质规则\/参考文章缺少逐篇合同落点/);
});

test('source tables reject off-table clauses and Markdown cannot contain binary NUL', () => {
  for (const suffix of ['\n必须执行隐藏动作\n', '\0']) {
    const changed = { ...hookSources, foundation: hookSources.foundation + suffix };
    assert.throws(() => collectSourceCoverage(SKILL_ROOT, changed), /非执行性对照表|NUL/);
  }
});

test('a Hook cannot render without its required fragment reference', () => {
  const verification = catalog.references
    .readHook('verification')
    .replace('<!-- rule:verification-epoch#actions -->', '');
  const changed = { ...catalog, references: { ...catalog.references, readHook: () => verification } };
  assert.throws(
    () => renderHook(changed, 'verification', 'single'),
    /缺少必需规则片段：verification-epoch#actions/,
  );
});

test('local destinations are document-relative, decoded, fragment-aware and independent of the target workspace', () => {
  const root = join(tmpdir(), 'synthetic skill 空格');
  const link = resolveDocumentLink(root, 'hooks/a.md', '../源%20文件.md?view=1#标题');
  assert.equal(link.path, join(root, '源 文件.md'));
  assert.equal(link.fragment, '标题');
  assert.equal(fileURLToPath(new URL(link.url)), link.path);
  assert.match(link.url, /%20/);
  assert.match(link.url, /\?view=1#/);
  assert.equal(resolveHookLink(root, 'foundation', '../SKILL.md#入口'), join(root, 'SKILL.md'));
  assert.equal(resolveDocumentLink(root, 'hooks/a.md', 'https://example.invalid/doc#x'), undefined);
  for (const href of ['../../escape.md', '%2e%2e/%2e%2e/escape.md', '../%00.md'])
    assert.throws(() => resolveDocumentLink(root, 'hooks/a.md', href), /越出/);
});

test('inline labels, destination titles, reference definitions and code examples are handled without altering prose', () => {
  const source =
    '[`名称`](../SKILL.md "标题")\n[引用]: <../SKILL.md#入口> "标题"\n`[不是链接](../missing.md)`\n```md\n[示例](../missing.md)\n```';
  assert.deepEqual(documentLinks(source), ['../SKILL.md', '../SKILL.md#入口']);
  const rendered = rewriteDocumentLinks(SKILL_ROOT, 'hooks/a.md', source);
  assert.ok(rendered.includes('[`名称`](file:'));
  assert.ok(rendered.includes(' "标题")'));
  assert.ok(rendered.includes('`[不是链接](../missing.md)`'));
  assert.ok(rendered.includes('[示例](../missing.md)'));
});

test('links fail on missing files, directories, bad anchors or symlink escapes; duplicate and Chinese headings work', (t) => {
  const root = mkdtempSync(join(tmpdir(), 'pi-hook-links-'));
  t.after(() => rmSync(root, { recursive: true, force: true }));
  mkdirSync(join(root, 'hooks'));
  writeFileSync(
    join(root, 'source.md'),
    '# 来源\n## 小节\n## 小节\n<a id="custom"></a>\n```\n## 假标题\n```\n',
  );
  assert.ok(headingAnchors(readFileSync(join(root, 'source.md'), 'utf8')).has('小节-1'));
  assert.equal(
    validateMarkdownLinks(root, 'hooks/a.md', '[x](../source.md#小节-1) [y](../source.md#custom)'),
    2,
  );
  for (const href of ['../missing.md', '.', '../source.md#不存在'])
    assert.throws(() => validateMarkdownLinks(root, 'hooks/a.md', `[x](${href})`), /链接目标|标题锚点/);
  assert.throws(() => validateMarkdownLinks(root, 'hooks/a.md', '[x](file:///tmp/source.md)'), /机器专属/);
  symlinkSync(join(SKILL_ROOT, 'SKILL.md'), join(root, 'escaped.md'));
  assert.throws(() => validateMarkdownLinks(root, 'hooks/a.md', '[x](../escaped.md)'), /符号链接/);
});

test('both routes retain all relevant contracts for observed capability changes, pause and a full observation window', () => {
  let peak = 0;
  for (const mode of ['single', 'multi'])
    for (const capabilityChanged of [false, true])
      for (const status of ['active', 'paused']) {
        const state = makeState(
          catalog,
          { sessionId: 'hook-test', cwd: tmpdir() },
          {
            mode,
            childCount: mode === 'single' ? 0 : 1,
            task: 'synthetic workspace, not the extension source directory',
          },
        );
        state.capabilityChanged = capabilityChanged;
        state.status = status;
        const w = new Workflow(catalog, state);
        for (let i = 0; i < 128; i++)
          w.observe({ id: `read-${i}`, tool: 'synthetic-read', effect: 'read', ok: true });
        const content = renderContext(w);
        peak = Math.max(peak, content.length);
        assert.ok(content.length <= MAX_CONTEXT);
        assert.ok(content.includes('[Hook:foundation]'));
        assert.ok(content.indexOf('[Hook:foundation]') < content.indexOf('{"mode":'));
        assert.ok(
          !documentLinks(content).some((target) => target.startsWith('../')),
          'module and hook links must not bind to the target project',
        );
        if (status === 'paused') assert.ok(content.includes('[Hook:recovery]'));
        assert.equal(content.includes('[Hook:entry]'), capabilityChanged);
      }
  assert.ok(
    peak >
      renderContext(
        new Workflow(
          catalog,
          makeState(
            catalog,
            { sessionId: 'default', cwd: tmpdir() },
            { mode: 'single', childCount: 0, task: 'synthetic' },
          ),
        ),
      ).length,
  );
});

test('context includes the complete route and only Hooks triggered by observed facts', () => {
  const state = makeState(
    catalog,
    { sessionId: 'hook-test', cwd: tmpdir() },
    { mode: 'multi', childCount: 1, task: 'synthetic task' },
  );
  const workflow = new Workflow(catalog, state);
  const context = renderContext(workflow);
  for (const id of ['MM01', 'MM04', 'MM07', 'coding-rule:hook-delegation']) assert.ok(context.includes(id));
  assert.ok(!context.includes('当前检查点'));
  assert.ok(!context.includes('[Hook:repair]'));
  workflow.state.capabilityChanged = true;
  assert.ok(renderContext(workflow).includes('[Hook:entry]'));
});

test('oversized state still blocks instead of truncating any execution guard', () => {
  const state = makeState(
    catalog,
    { sessionId: 'oversize', cwd: tmpdir() },
    { mode: 'single', childCount: 0, task: 'synthetic' },
  );
  state.reason = 'x'.repeat(MAX_CONTEXT);
  assert.throws(() => renderContext(new Workflow(catalog, state)), /超出96000字符上限.*不能截断守卫/);
});
