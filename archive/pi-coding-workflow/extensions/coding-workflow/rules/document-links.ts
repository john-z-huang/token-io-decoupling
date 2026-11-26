import { dirname, isAbsolute, relative, resolve, sep } from "node:path";
import { pathToFileURL } from "node:url";
import type { Catalog, HookId } from "../catalog.ts";

/** Resolve against the resource document, never the user's unrelated working directory. */
export function resolveDocumentLink(
  root: string,
  document: string,
  target: string,
): { path: string; fragment: string; url: string } | undefined {
  const href = target.replace(/^<|>$/g, "");
  if (/^[a-z][a-z0-9+.-]*:/i.test(href) || href.startsWith("//")) return undefined;
  const [beforeHash, ...hash] = href.split("#");
  const [file, ...query] = beforeHash.split("?");
  const source = resolve(root, document);
  const path = file ? resolve(dirname(source), decodeURIComponent(file)) : source;
  const rel = relative(resolve(root), path);
  if (rel === ".." || rel.startsWith(".." + sep) || isAbsolute(rel) || path.includes("\0"))
    throw new Error(`文档链接越出 Skill：${document} -> ${target}`);
  const fragment = decodeURIComponent(hash.join("#"));
  const url = pathToFileURL(path);
  if (query.length) url.search = query.join("?");
  if (hash.length) url.hash = hash.join("#");
  return { path, fragment, url: url.href };
}

type LinkTransform = (target: string) => string;
const INLINE_LINK = /(`+)[^\n]*?\1|(!?\[[^\]\n]*\]\()(<[^>\n]+>|[^\s)]+)(?=[ \t]*(?:\)|["']))/g;
const REFERENCE_LINK = /^( {0,3}\[[^\]\n]+\]:[ \t]*)(<[^>\n]+>|[^\s]+)(?=[ \t]|$)/;
const FENCE = /^ {0,3}(`{3,}|~{3,})/;

function replaceDestination(prefix: string, target: string, transform: LinkTransform): string {
  if (target.startsWith("<")) return prefix + "<" + transform(target.slice(1, -1)) + ">";
  return prefix + transform(target);
}

function rewriteInlineLinks(line: string, transform: LinkTransform): string {
  let result = "";
  let cursor = 0;
  for (const match of line.matchAll(INLINE_LINK)) {
    const [, code, prefix, target] = match;
    if (code || !prefix) continue;
    result += line.slice(cursor, match.index) + replaceDestination(prefix, target, transform);
    cursor = match.index + match[0].length;
  }
  return result + line.slice(cursor);
}

function rewriteLinkLine(line: string, transform: LinkTransform): string {
  return rewriteInlineLinks(line, transform).replace(
    REFERENCE_LINK,
    (_match, prefix: string, target: string) => replaceDestination(prefix, target, transform),
  );
}

export function* markdownLines(markdown: string): Iterable<{ line: string; fenced: boolean }> {
  let fence: string | undefined;
  for (const line of markdown.split("\n")) {
    const marker = FENCE.exec(line);
    if (fence) {
      const closing = marker && marker[1][0] === fence[0] && marker[1].length >= fence.length;
      if (closing && !line.slice(marker[0].length).trim()) fence = undefined;
      yield { line, fenced: true };
      continue;
    }
    if (marker) fence = marker[1];
    yield { line, fenced: Boolean(marker) };
  }
}

// 只转换资源链接，保留代码围栏、行内代码、链接标题和目标的尖括号。
export function mapDocumentLinks(markdown: string, transform: LinkTransform): string {
  return Array.from(markdownLines(markdown), ({ line, fenced }) =>
    fenced ? line : rewriteLinkLine(line, transform),
  ).join("\n");
}

export function documentLinks(markdown: string): string[] {
  const links: string[] = [];
  mapDocumentLinks(markdown, (target) => {
    links.push(target);
    return target;
  });
  return links;
}

export function rewriteDocumentLinks(root: string, document: string, markdown: string): string {
  return mapDocumentLinks(markdown, (target) => resolveDocumentLink(root, document, target)?.url ?? target);
}

export function ruleLink(document: string, fragment?: string): string {
  return `coding-rule:${document}${fragment ? `#${fragment}` : ""}`;
}

type ReferenceDocument = ReturnType<Catalog["references"]["document"]>;
type DocumentLink = NonNullable<ReturnType<typeof resolveDocumentLink>>;

function findRuleFragment(document: ReferenceDocument, fragment: string, yaml: boolean) {
  return document.fragments.find((entry) =>
    yaml ? entry.id === fragment : entry.kind === "section" && entry.anchor === fragment,
  );
}

function ruleSourceUrl(
  catalog: Catalog,
  document: ReferenceDocument,
  { link, yaml }: { link: DocumentLink; yaml: boolean },
): string {
  const sourcePath = catalog.references.sourceForPath(document.path);
  if (!sourcePath) throw new Error(`DSL 链接缺少规则源文件：${document.path}`);
  const original = new URL(link.url);
  const rule = pathToFileURL(resolve(catalog.root, sourcePath));
  rule.search = original.search;
  rule.hash = yaml ? original.hash : (document.sectionIds.get(link.fragment) ?? original.hash);
  return rule.href;
}

function workflowLink(catalog: Catalog, source: string, target: string): string {
  const link = resolveDocumentLink(catalog.root, source, target);
  if (!link) return target;
  const path = relative(catalog.root, link.path).split(sep).join("/");
  const yaml = path.endsWith(".yaml");
  const exportPath = yaml ? path.replace(/\.yaml$/, ".md") : path;
  const document = catalog.references.documentForPath(exportPath);
  if (!document) {
    if (yaml) throw new Error(`DSL 链接缺少规则文档：${source} -> ${target}`);
    return link.url;
  }
  return indexedLink(catalog, document, { link, yaml, source, target });
}

function indexedLink(
  catalog: Catalog,
  document: ReferenceDocument,
  { link, yaml, source, target }: { link: DocumentLink; yaml: boolean; source: string; target: string },
): string {
  const fragment = findRuleFragment(document, link.fragment, yaml);
  if (fragment) return ruleLink(document.id, fragment.id);
  if (!link.fragment && (document.fragments.length || document.id === "hook-readme"))
    return ruleLink(document.id);
  if (yaml && link.fragment && ![...document.sectionIds.values()].includes(link.fragment)) {
    throw new Error(`DSL 链接缺少规则片段：${source} -> ${target}`);
  }
  return ruleSourceUrl(catalog, document, { link, yaml });
}

export function rewriteWorkflowLinks(catalog: Catalog, source: string, markdown: string): string {
  return mapDocumentLinks(markdown, (target) => workflowLink(catalog, source, target));
}

export function resolveHookLink(root: string, hook: HookId, target: string): string {
  const link = resolveDocumentLink(root, `hooks/${hook}.md`, target);
  if (!link) throw new Error(`不是本地来源链接：${target}`);
  return link.path;
}
