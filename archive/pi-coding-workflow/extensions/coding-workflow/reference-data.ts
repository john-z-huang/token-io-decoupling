import { createHash } from "node:crypto";
import { readFileSync, readdirSync, realpathSync } from "node:fs";
import { join } from "node:path";
import { isAlias, isNode, parseDocument, visit } from "yaml";
import {
  DOCUMENT_ID,
  TITLE,
  readBlocks,
  readMapping,
  readSpacing,
  readText,
  type RuleEntry,
} from "./rules/blocks.ts";
import { indexFragments, renderBlocks, type Fragment } from "./rules/fragments.ts";

export { headingSlug } from "./rules/fragments.ts";

interface ReferenceDocument {
  id: string;
  path: string;
  title: string;
  fragments: Fragment[];
  sectionIds: Map<string, string>;
}

interface HookBody {
  id: string;
  activation: unknown;
  render: () => string;
}

interface IndexedDocument {
  document: ReferenceDocument;
  file: string;
  hash: string;
  renderers: Map<string, () => string>;
  hook?: HookBody;
  route?: () => string;
}

interface ReferenceData {
  digest: string;
  document(id: string): ReferenceDocument;
  readFragment(documentId: string, id: string): string;
  readRoute(id: string): string;
  readHook(id: string): string;
  hookActivation(id: string): unknown;
  documentPaths(): IterableIterator<string>;
  documentForPath(path: string): ReferenceDocument | undefined;
  sourceForPath(path: string): string | undefined;
}

const sha256 = (body: Buffer) => createHash("sha256").update(body).digest("hex");

function readSource(root: string, file: string): Buffer {
  const path = join(root, file);
  if (realpathSync(path) !== path) throw new Error(`规则源不允许符号链接：${path}`);
  return readFileSync(path);
}

function yamlFiles(root: string, directory: string): string[] {
  return readdirSync(join(root, directory), { withFileTypes: true }).flatMap((item) => {
    const file = `${directory}/${item.name}`;
    if (item.isSymbolicLink()) throw new Error(`规则源不允许符号链接：${file}`);
    if (item.isDirectory()) return yamlFiles(root, file);
    return item.isFile() && item.name.endsWith(".yaml") && file !== "hooks/SOURCE_COVERAGE.yaml"
      ? [file]
      : [];
  });
}

function parseSource(content: Buffer, file: string): Record<string, unknown> {
  const yaml = parseDocument(content.toString("utf8"), { uniqueKeys: true, schema: "core" });
  const issue = yaml.errors[0] ?? yaml.warnings[0];
  if (issue) throw new Error(`无效的规则 YAML：${file}：${issue.message}`);
  visit(yaml, (_key, node) => {
    if (isAlias(node) || (isNode(node) && "anchor" in node && node.anchor)) {
      throw new Error(`规则 YAML 不允许锚点或别名：${file}`);
    }
  });
  return readMapping(yaml.toJS({ maxAliasCount: 0 }), file);
}

function readHeader(raw: Record<string, unknown>, file: string) {
  const id = readText(raw.id, file, DOCUMENT_ID);
  const path = file.replace(/\.yaml$/, ".md");
  const hookFile = file.startsWith("hooks/");
  const hookId = file === "hooks/README.yaml" ? "readme" : file.slice(6, -5);
  if (raw.schema_version !== 1 || raw.markdown_path !== path || (hookFile && id !== hookId)) {
    throw new Error(`规则 YAML 的版本、路径或 Hook ID 不匹配：${file}`);
  }
  const title = readText(raw.title, file, TITLE);
  const gap = readSpacing(raw.blank_lines_after_title, file, 1) ?? 2;
  return { id, path, hookFile, title, gap };
}

function hookBody(
  raw: Record<string, unknown>,
  header: ReturnType<typeof readHeader>,
  blocks: RuleEntry[],
): HookBody | undefined {
  if (!header.hookFile || raw.document_type !== "hook-contract") return undefined;
  const execution = blocks.filter(({ id }) => !["flowchart", "checkpoints", "sources"].includes(id));
  return {
    id: header.id,
    activation: raw.activate_on,
    render: () => `# ${header.title}${"\n".repeat(header.gap)}${renderBlocks(execution, 2)}`,
  };
}

function indexDocument(file: string, content: Buffer): IndexedDocument {
  const raw = parseSource(content, file);
  const header = readHeader(raw, file);
  const blocks = readBlocks(raw.blocks, file);
  const { fragments, renderers, sectionIds } = indexFragments(header.title, blocks);
  const id = header.hookFile ? `hook-${header.id}` : header.id;
  return {
    file,
    hash: sha256(content),
    document: { id, path: header.path, title: header.title, fragments, sectionIds },
    renderers,
    hook: hookBody(raw, header, blocks),
    route:
      raw.document_type === "workflow-route" || id === "hook-readme"
        ? () =>
            renderBlocks(
              blocks.filter(({ id }) => id !== "flowchart"),
              2,
            )
        : undefined,
  };
}

function indexSources(root: string) {
  const digest = createHash("sha256");
  const byId = new Map<string, IndexedDocument>();
  const byPath = new Map<string, IndexedDocument>();
  const hooks = new Map<string, HookBody>();
  const files = [
    ...["references", "coding-workflows", "hooks"].flatMap((directory) => yamlFiles(root, directory)),
    "SKILL.yaml",
    "workflows/coding.yaml",
  ].sort();
  for (const file of files) {
    const content = readSource(root, file);
    const entry = indexDocument(file, content);
    const { id, path } = entry.document;
    if (byId.has(id)) throw new Error(`重复的规则文档 ID：${id}`);
    byId.set(id, entry);
    byPath.set(path, entry);
    if (entry.hook) hooks.set(entry.hook.id, entry.hook);
    digest.update(file).update("\0").update(content).update("\0");
  }
  return { digest: digest.digest("hex"), byId, byPath, hooks };
}

function openBodies(root: string, { byId, hooks }: ReturnType<typeof indexSources>) {
  const verified = new Set<string>();
  const cache = new Map<string, string>();

  function readBody(owner: string, key: string, render: () => string): string {
    const cached = cache.get(key);
    if (cached !== undefined) return cached;
    const source = byId.get(owner);
    if (!source) throw new Error(`规则 DSL 缺少文档：${owner}`);
    if (!verified.has(owner)) {
      if (sha256(readSource(root, source.file)) !== source.hash) {
        throw new Error(`规则 YAML Hash 不匹配：${source.file}`);
      }
      verified.add(owner);
    }
    const body = render().trimEnd();
    if (!body) throw new Error(`规则正文为空：${key}`);
    cache.set(key, body);
    return body;
  }

  return {
    readFragment(documentId: string, id: string) {
      const key = `${documentId}#${id}`;
      const render = byId.get(documentId)?.renderers.get(id);
      if (!render) throw new Error(`规则 DSL 缺少片段：${key}`);
      return readBody(documentId, key, render);
    },
    readRoute(id: string) {
      const render = byId.get(id)?.route;
      if (!render) throw new Error("规则 DSL 缺少路线：" + id);
      return readBody(id, "routes/" + id, render);
    },
    readHook(id: string) {
      const hook = hooks.get(id);
      if (!hook) throw new Error(`规则 DSL 缺少 Hook：${id}`);
      return readBody(`hook-${id}`, `hooks/${id}`, hook.render);
    },
  };
}

export function loadReferenceData(root: string): ReferenceData {
  const rules = realpathSync(root);
  const index = indexSources(rules);
  return {
    digest: index.digest,
    document(id) {
      const entry = index.byId.get(id);
      if (!entry) throw new Error(`规则 DSL 缺少文档：${id}`);
      return entry.document;
    },
    ...openBodies(rules, index),
    hookActivation: (id) => index.hooks.get(id)?.activation,
    documentPaths: () => index.byPath.keys(),
    documentForPath: (path) => index.byPath.get(path)?.document,
    sourceForPath: (path) => index.byPath.get(path)?.file,
  };
}
