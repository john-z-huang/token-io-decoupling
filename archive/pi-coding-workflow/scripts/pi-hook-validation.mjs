// 离线核对 Markdown 链接和规则来源对照，供构建检查与测试共用。
import assert from 'node:assert/strict';
import { existsSync, readFileSync, readdirSync, realpathSync, statSync } from 'node:fs';
import { basename, dirname, isAbsolute, join, relative, sep } from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  documentLinks,
  headingSlug,
  HOOK_IDS,
  WORKFLOW_DIR,
  resolveDocumentLink,
} from '../extensions/coding-workflow/catalog.ts';
import { markdownLines } from '../extensions/coding-workflow/rules/document-links.ts';

export const SKILL_ROOT = fileURLToPath(new URL('../docs/skill', import.meta.url));
const PROJECT_GUIDES = new Set(['../project/PI_EXTENSION.md', '../project/WORKFLOW_ARCHITECTURE.md']);

const L1_HOOKS = {
  'context-exchange': ['context'],
  delegation: ['delegation', 'session'],
  'execution-control': ['execution'],
  'execution-planning': ['planning'],
  'session-runtime': ['session', 'audit'],
  'workflow-navigation': ['navigation'],
};
const L2_HOOKS = {
  'entry-and-context': ['entry', 'planning'],
  'decision-and-execution': ['execution', 'planning'],
  'verification-and-repair': ['verification', 'repair'],
  'completion-and-effects': ['documentation', 'delivery'],
};
const OVERRIDES = {
  'candidate-compliance': ['materialization'],
  'output-materialization': ['materialization'],
  'decisions-advisory': ['advisory'],
  'decision-context-generation': ['advisory', 'planning'],
  'workflow-routing-advice': ['navigation', 'advisory'],
  'workflow-module-contract': ['recovery'],
  'LSP-MCP-Tools': ['context', 'session'],
  'runtime-provider-support': ['foundation', 'session', 'delegation'],
  'session-context-firewall': ['context'],
  'reasoning-summary-visibility': ['audit'],
  'session-audit-visibility': ['audit'],
};

function layerHooks(parts) {
  const layer = parts.findIndex((part) => part.startsWith('layer-'));
  if (layer < 0) return undefined;
  const number = parts[layer].slice(6, 8);
  if (number === '03') return ['navigation', 'execution'];
  if (number !== '01' && number !== '02') return undefined;
  const group = parts[layer + 1];
  if (!group || group.endsWith('.md')) return ['navigation'];
  const table = number === '01' ? L1_HOOKS : L2_HOOKS;
  return Object.hasOwn(table, group) ? table[group] : undefined;
}

export function classifySource(path) {
  const parts = path.split('/');
  const stem = parts.at(-1).replace(/\.md$/, '');
  const kind = stem === 'README' ? 'navigation' : 'rule';
  if (parts.includes('multimodal')) return { path, hooks: ['foundation'], kind: 'reference' };
  if (Object.hasOwn(OVERRIDES, stem)) return { path, hooks: OVERRIDES[stem], kind };
  if (parts.includes('share') || path === 'SKILL.md') return { path, hooks: ['foundation'], kind };
  const hooks = layerHooks(parts);
  if (hooks) return { path, hooks, kind };
  if (path === 'workflows/coding.md') return { path, hooks: ['foundation', 'navigation'], kind };
  throw new Error(`没有 Hook 归属的规则：${path}`);
}

function markdownFiles(root) {
  return readdirSync(root, { withFileTypes: true })
    .flatMap((entry) => {
      assert.ok(!entry.isSymbolicLink(), `规则源不允许符号链接：${entry.name}`);
      const path = join(root, entry.name);
      if (entry.isDirectory()) return markdownFiles(path);
      return entry.name.endsWith('.md') ? [path] : [];
    })
    .sort();
}

export function readHookSources(root) {
  return Object.fromEntries(
    HOOK_IDS.map((id) => [id, readFileSync(join(root, 'hooks', `${id}.md`), 'utf8')]),
  );
}

export function headingAnchors(markdown) {
  const anchors = new Set();
  const counts = new Map();
  for (const { line, fenced } of markdownLines(markdown)) {
    if (fenced) continue;
    for (const match of line.matchAll(/<(?:a|h[1-6])\b[^>]*\b(?:id|name)=["']([^"']+)["']/gi)) {
      anchors.add(match[1]);
    }
    const heading = line.match(/^ {0,3}#{1,6}\s+(.+?)(?:\s+#+\s*)?$/);
    if (!heading) continue;
    const base = headingSlug(heading[1]);
    const duplicates = counts.get(base) ?? 0;
    counts.set(base, duplicates + 1);
    anchors.add(duplicates ? `${base}-${duplicates}` : base);
  }
  return anchors;
}

function inside(root, path) {
  const rel = relative(root, path);
  return rel !== '..' && !rel.startsWith('..' + sep) && !isAbsolute(rel);
}

function resolveSkillLink(root, document, target) {
  const link = resolveDocumentLink(dirname(root), join(basename(root), document), target);
  if (!link) return;
  const projectGuide = PROJECT_GUIDES.has(relative(root, link.path).split(sep).join('/'));
  assert.ok(projectGuide || inside(root, link.path), `${document}: 文档链接越出 Skill ${target}`);
  return { ...link, projectGuide };
}

export function validateMarkdownLinks(root, document, markdown) {
  let checked = 0;
  for (const target of documentLinks(markdown)) {
    assert.ok(!/^file:/i.test(target), `${document}: 磁盘文档不得写入机器专属 file URL`);
    const link = resolveSkillLink(root, document, target);
    if (!link) continue; // 此处只核对本地链接，外部 URL 不发网络请求。
    assert.ok(
      existsSync(link.path) && statSync(link.path).isFile(),
      `${document}: 链接目标不存在或不是文件 ${target}`,
    );
    const physical = realpathSync(link.path);
    const allowed = link.projectGuide ? physical === link.path : inside(realpathSync(root), physical);
    assert.ok(allowed, `${document}: 来源通过符号链接越出 Skill ${target}`);
    if (link.fragment)
      assert.ok(
        headingAnchors(readFileSync(link.path, 'utf8')).has(link.fragment),
        `${document}: 标题锚点不存在 ${target}`,
      );
    checked++;
  }
  return checked;
}

function sourceTable(markdown, hook) {
  assert.ok(!markdown.includes('\0'), `${hook}: Markdown中不得嵌入NUL字节`);
  const sections = ['触发条件', '执行要求', '退出与阻断', '重新核验', '规则来源'];
  const headings = sections.map((section) => `\n## ${section}\n`);
  const positions = headings.map((heading) => markdown.indexOf(heading));
  const inOrder = positions.every(
    (position, index) => position >= 0 && (index === 0 || position > positions[index - 1]),
  );
  assert.ok(inOrder, `${hook}: 合同章节缺失或次序错误`);

  const table = markdown.slice(positions.at(-1) + headings.at(-1).length).trim();
  const rows = table.split('\n').filter((line) => line.trim());
  assert.ok(
    rows.every((line) => line.startsWith('|')),
    `${hook}: 规则来源只放非执行性对照表，动作条款须置于执行/退出/重核章节`,
  );
  assert.ok(/^\|\s*来源\s*\|\s*本合同落点\s*\|/m.test(table), `${hook}: 缺少逐篇来源与合同落点表`);
  return table;
}

function registerSourceReferences(root, hooks, consumingHooks) {
  for (const id of HOOK_IDS) {
    const table = sourceTable(hooks[id], id);
    let referencesFound = 0;
    for (const target of documentLinks(table)) {
      const link = resolveSkillLink(root, `hooks/${id}.md`, target);
      if (!link) continue;
      const source = relative(root, link.path).split(sep).join('/');
      const registered = consumingHooks.get(source);
      if (!registered) continue;
      registered.add(id);
      referencesFound++;
    }
    assert.ok(referencesFound > 0, `${id}: 没有真实规则来源`);
  }
}

export function collectSourceCoverage(root, hooks = readHookSources(root)) {
  const sourcePaths = markdownFiles(root)
    .map((path) => relative(root, path).split(sep).join('/'))
    .filter((path) => !path.startsWith('hooks/') && !path.startsWith(`${WORKFLOW_DIR}/`));
  const coverage = sourcePaths.map(classifySource);
  const consumingHooks = new Map(coverage.map((row) => [row.path, new Set()]));
  registerSourceReferences(root, hooks, consumingHooks);
  const missing = coverage.filter((row) => row.kind !== 'navigation' && !consumingHooks.get(row.path).size);
  assert.deepEqual(
    missing.map((row) => row.path),
    [],
    '实质规则/参考文章缺少逐篇合同落点',
  );
  return coverage.map((row) => ({
    ...row,
    hooks: [...consumingHooks.get(row.path)],
    declaredHooks: row.hooks,
  }));
}

export function coverageYaml(rows) {
  const lines = [
    '# yaml-language-server: $schema=../hook-coverage.schema.json',
    '# 由 node scripts/check-pi-hooks.mjs --write-coverage 根据 Hook 来源块生成。',
    'schema_version: 1',
    'document_type: hook-coverage',
    'id: source-coverage',
    'markdown_path: hooks/SOURCE_COVERAGE.md',
    'title: Hook 来源整合对照',
    'rows:',
  ];
  for (const row of rows) {
    const source = `../${row.path.replace(/\.md$/, '.yaml')}`;
    const hooks = row.hooks.length ? row.hooks : row.declaredHooks;
    lines.push(
      `  - source: ${JSON.stringify(source)}`,
      `    kind: ${row.kind}`,
      `    hooks: ${JSON.stringify(hooks)}`,
      `    explicit: ${row.hooks.length > 0}`,
    );
  }
  return lines.join('\n') + '\n';
}
