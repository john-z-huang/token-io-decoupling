import { readText, type Applicability, type RuleEntry } from "./blocks.ts";

export type Fragment = { id: string; title: string } & (
  | { kind: "checkpoint"; applicability?: Applicability }
  | { kind: "markdown" }
  | { kind: "section"; anchor: string }
  | { kind: "route_step"; phase: string; hook: string }
);

interface FragmentIndex {
  fragments: Fragment[];
  renderers: Map<string, () => string>;
  sectionIds: Map<string, string>;
}

export function headingSlug(title: string): string {
  return title
    .replace(/\[([^\]]+)\]\([^)]*\)/g, "$1")
    .replace(/<[^>]*>/g, "")
    .toLowerCase()
    .replace(/[^\p{L}\p{N}\p{M}_\-\s]/gu, "")
    .replace(/ /g, "-");
}

function renderEntry({ id, block }: RuleEntry, level: number, number?: number): string {
  if (block.kind === "section") {
    return `${"#".repeat(level)} ${block.title}\n\n${renderBlocks(block.children, level + 1)}`;
  }
  if (block.kind === "rule_include") return `<!-- rule:${block.document}#${block.fragment} -->`;
  const text = block.text.replace(/\n+$/, "");
  if (block.kind === "markdown" || number === undefined) return text;
  const [first, ...rest] = text.split("\n");
  const indent = " ".repeat(String(number).length + 2);
  const continuation = rest.map((line) => "\n" + (line ? indent + line : "")).join("");
  return `${number}. **${id} — ${block.title}** ${first}${continuation}`;
}

function spacing(block: RuleEntry["block"], continuingList: boolean): number {
  const defaultGap = continuingList ? 0 : 1;
  return block.kind === "section" ? (block.gap ?? defaultGap) : defaultGap;
}

export function renderBlocks(entries: RuleEntry[], level: number): string {
  const body: string[] = [];
  let previous: RuleEntry["block"]["kind"] | undefined;
  let number = 0;
  for (const entry of entries) {
    const { block } = entry;
    const numbered = block.kind === "checkpoint" || block.kind === "route_step";
    const continueList = numbered && previous === block.kind;
    if (body.length) body.push("\n".repeat(1 + spacing(block, continueList)));
    if (numbered) number = continueList ? number + 1 : 1;
    body.push(renderEntry(entry, level, numbered ? number : undefined));
    previous = block.kind;
  }
  return body.join("");
}

function appendFragment(index: FragmentIndex, fragment: Fragment, render: () => string): void {
  index.fragments.push(fragment);
  index.renderers.set(fragment.id, render);
}

function indexContent(index: FragmentIndex, { id, block }: RuleEntry): void {
  switch (block.kind) {
    case "route_step": {
      const { title, kind, phase, hook } = block;
      return appendFragment(index, { id, title, kind, phase, hook }, () => block.text);
    }
    case "checkpoint": {
      const { title, kind, applicability } = block;
      return appendFragment(index, { id, title, kind, applicability }, () => block.text);
    }
    case "markdown":
      if (block.expose) {
        appendFragment(index, { id, title: readText(block.title, id), kind: block.kind }, () => block.text);
      }
  }
}

export function indexFragments(title: string, entries: RuleEntry[]): FragmentIndex {
  const index: FragmentIndex = { fragments: [], renderers: new Map(), sectionIds: new Map() };
  const counts = new Map([[headingSlug(title), 1]]);
  function visit(items: RuleEntry[], level: number): void {
    for (const entry of items) {
      const { id, block } = entry;
      if (block.kind !== "section") {
        indexContent(index, entry);
        continue;
      }
      const base = headingSlug(block.title);
      const count = counts.get(base) ?? 0;
      counts.set(base, count + 1);
      const anchor = count ? `${base}-${count}` : base;
      index.sectionIds.set(anchor, id);
      if (block.expose) {
        appendFragment(index, { id, title: block.title, kind: block.kind, anchor }, () =>
          renderBlocks(block.children, level + 1),
        );
      }
      visit(block.children, level + 1);
    }
  }
  visit(entries, 2);
  return index;
}
