export type Applicability = "optional" | "sub_agent";

type Block =
  | { kind: "markdown"; text: string; title?: string; expose: boolean }
  | { kind: "checkpoint"; text: string; title: string; applicability?: Applicability }
  | { kind: "route_step"; text: string; title: string; phase: string; hook: string }
  | { kind: "section"; title: string; children: RuleEntry[]; expose: boolean; gap?: number }
  | { kind: "rule_include"; document: string; fragment: string };

export interface RuleEntry {
  id: string;
  block: Block;
}

export const DOCUMENT_ID = /^[a-z][a-z0-9-]*$/;
export const TITLE = /^[^\r\n]+$/;
const BLOCK_ID = /^[A-Za-z][A-Za-z0-9-]*$/;

export function readMapping(value: unknown, path: string): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error(`DSL 应为映射：${path}`);
  return value as Record<string, unknown>;
}

export function readText(value: unknown, path: string, pattern?: RegExp): string {
  if (
    typeof value !== "string" ||
    !value.trim() ||
    value.includes("\0") ||
    (pattern && !pattern.test(value))
  ) {
    throw new Error(`DSL 字段无效：${path}`);
  }
  return value;
}

export function readSpacing(value: unknown, path: string, minimum: number): number | undefined {
  if (value === undefined) return undefined;
  if (typeof value !== "number" || !Number.isSafeInteger(value) || value < minimum) {
    throw new Error(`DSL 空行数无效：${path}`);
  }
  return value;
}

function readCheckpoint(data: Record<string, unknown>, key: string): Block {
  const { applicability } = data;
  if (applicability !== undefined && applicability !== "optional" && applicability !== "sub_agent") {
    throw new Error(`检查点适用条件无效：${key}`);
  }
  return {
    kind: "checkpoint",
    text: readText(data.text, key),
    title: readText(data.title, key, TITLE),
    applicability,
  };
}

function readRouteStep(data: Record<string, unknown>, key: string): Block {
  const text = readText(data.text, key);
  const hook = readText(data.hook, key, DOCUMENT_ID);
  if (!text.includes(`](../hooks/${hook}.yaml)`)) {
    throw new Error(`路线契约变化，Hook 与 DSL 链接不一致：${key}`);
  }
  return {
    kind: "route_step",
    text,
    title: readText(data.title, key, TITLE),
    phase: readText(data.phase, key, DOCUMENT_ID),
    hook,
  };
}

function readBlock(
  data: Record<string, unknown>,
  { file, key, seen }: { file: string; key: string; seen: Set<string> },
): Block {
  const { kind } = data;
  switch (kind) {
    case "section":
      return {
        kind,
        title: readText(data.title, key, TITLE),
        children: readBlocks(data.blocks, file, seen),
        expose: data.expose === true,
        gap: readSpacing(data.blank_lines_before, key, 0),
      };
    case "markdown":
      return {
        kind,
        text: readText(data.text, key),
        expose: data.expose === true,
        title: data.expose || data.title !== undefined ? readText(data.title, key, TITLE) : undefined,
      };
    case "checkpoint":
      return readCheckpoint(data, key);
    case "route_step":
      return readRouteStep(data, key);
    case "rule_include":
      return {
        kind,
        document: readText(data.document, key, DOCUMENT_ID),
        fragment: readText(data.fragment, key, BLOCK_ID),
      };
    default:
      throw new Error(`DSL 块类型无效：${key}`);
  }
}

function readEntry(item: unknown, file: string, seen: Set<string>): RuleEntry {
  const fields = Object.entries(readMapping(item, file));
  if (fields.length !== 1) throw new Error(`DSL 块须有一个 ID：${file}`);
  const [id, raw] = fields[0];
  const key = `${file}#${id}`;
  if (!BLOCK_ID.test(id) || seen.has(id)) throw new Error(`DSL 块 ID 无效或重复：${key}`);
  seen.add(id);
  const data = readMapping(raw, key);
  if (data.expose !== undefined && typeof data.expose !== "boolean") {
    throw new Error(`DSL expose 无效：${key}`);
  }
  return { id, block: readBlock(data, { file, key, seen }) };
}

export function readBlocks(value: unknown, file: string, seen = new Set<string>()): RuleEntry[] {
  if (!Array.isArray(value) || !value.length) throw new Error(`DSL 块列表为空或无效：${file}`);
  return value.map((item) => readEntry(item, file, seen));
}
