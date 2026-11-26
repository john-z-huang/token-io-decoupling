import type { ExtensionAPI, ExtensionContext } from "@earendil-works/pi-coding-agent";
import type { Mode } from "./catalog.ts";

export type Source = "explicit" | "default";
export interface Audit {
  audit_mode: string;
  root_reasoning_cadence: string;
  worker_reasoning_cadence: string;
  source: Record<AuditKey, Source>;
}
type AuditKey = "audit_mode" | "root_reasoning_cadence" | "worker_reasoning_cadence";
export interface StartupAnswers {
  mode: Mode;
  count: number;
  audit: Audit;
}
export interface StartupInput {
  mode?: string;
  count?: string;
  defaults?: boolean;
  audit?: Partial<Record<AuditKey, string>>;
}
interface Draft {
  mode?: Mode;
  count?: number;
  audit: Partial<Omit<Audit, "source">> & { source: Partial<Record<AuditKey, Source>> };
}
const FIELDS = [
  {
    key: "audit_mode",
    flag: "coding-audit-mode",
    values: ["economy", "balanced", "full"],
    fallback: "balanced",
  },
  {
    key: "root_reasoning_cadence",
    flag: "coding-root-cadence",
    values: ["full", "milestone_only", "off"],
    fallback: "milestone_only",
  },
  {
    key: "worker_reasoning_cadence",
    flag: "coding-worker-cadence",
    values: ["full", "milestone_only", "off"],
    fallback: "full",
  },
] as const;
type AuditField = (typeof FIELDS)[number];

interface StartupPrompt {
  context: ExtensionContext;
  current: () => void;
}

interface StartupOptions {
  saved?: StartupAnswers;
  current?: () => void;
}

export interface StartupRequest {
  input: StartupInput;
  task: string;
}

const cancelled = () =>
  new Error("启动已取消/答案未完成；没有创建 Workflow。请重新 /coding start 或显式提交启动答案");

async function select(
  { context, current }: StartupPrompt,
  title: string,
  values: readonly string[],
): Promise<string> {
  current();
  if (!context.hasUI) {
    throw new Error(
      `启动答案缺失：${title}；非 UI 请显式提交 --coding-mode 及审计字段或 --coding-audit-defaults`,
    );
  }
  const value = await context.ui.select(title, [...values]);
  current();
  if (value === undefined) throw cancelled();
  if (!values.includes(value)) throw new Error(`无效启动答案：${title}`);
  return value;
}

function parseCount(value: string): number {
  const count = Number(value);
  if (!/^[1-9]\d*$/.test(value) || !Number.isSafeInteger(count)) {
    throw new Error("multi 数量必须为有效正整数；不能回退默认1");
  }
  return count;
}

async function collectMode(draft: Draft, prompt: StartupPrompt): Promise<void> {
  if (draft.mode) return;
  const customBudget = "multi（自定义数量）";
  const choice = await select(prompt, "1. Coding 模式", ["multi（默认预算1）", "single", customBudget]);
  draft.mode = choice === "single" ? "single" : "multi";
  if (draft.mode === "single" && draft.count !== undefined) throw new Error("single 不接受子代理数量");
  if (choice !== customBudget || draft.count !== undefined) return;
  prompt.current();
  const count = await prompt.context.ui.input("multi 子代理预算：正整数");
  prompt.current();
  if (count === undefined) throw cancelled();
  draft.count = parseCount(count);
}

function setAuditField(
  draft: Draft,
  key: AuditKey,
  { value, source }: { value: string; source: Source },
): void {
  draft.audit[key] = value;
  draft.audit.source[key] = source;
}

async function collectAudit(draft: Draft, prompt: StartupPrompt): Promise<void> {
  const missing = FIELDS.filter(({ key }) => draft.audit[key] === undefined);
  if (!missing.length) return;
  const defaults = "使用默认（balanced / milestone_only / full）";
  const choice = await select(prompt, "2. 审计可见性（仅安全摘要偏好，不代表日志能力）", [
    defaults,
    "定制未提供字段",
  ]);
  for (const field of missing) {
    const value = choice === defaults ? field.fallback : await select(prompt, field.key, field.values);
    setAuditField(draft, field.key, { value, source: choice === defaults ? "default" : "explicit" });
  }
}

// 命令和 CLI 参数共用问题顺序，已给出的答案可跳过对应问题。
export const STARTUP_QUESTIONS = [
  { id: "mode", collect: collectMode },
  { id: "audit", collect: collectAudit },
] as const;

function validCount({ mode, count }: StartupAnswers): boolean {
  return Number.isSafeInteger(count) && (mode === "single" ? count === 0 : count >= 1);
}

function acceptsAuditValue(field: AuditField, value: unknown): boolean {
  return field.values.some((allowed) => allowed === value);
}

export function validateAnswers(value: unknown): StartupAnswers {
  const answers = value as StartupAnswers;
  if (!answers || !["single", "multi"].includes(answers.mode) || !validCount(answers)) {
    throw new Error("启动模式/预算快照无效");
  }
  for (const field of FIELDS) {
    const source = answers.audit?.source?.[field.key];
    if (!acceptsAuditValue(field, answers.audit?.[field.key]) || !["explicit", "default"].includes(source)) {
      throw new Error(`审计启动快照无效：${field.key}`);
    }
  }
  return structuredClone(answers);
}

function applyMode(draft: Draft, requested: StartupInput["mode"], saved?: StartupAnswers): void {
  if (requested === undefined) return;
  if (requested !== "single" && requested !== "multi") throw new Error("--coding-mode 只接受 single/multi");
  if (saved && saved.mode !== requested) throw new Error("同 Session 模式已锁定；请新建 Session");
  draft.mode = requested;
}

function applyBudget(draft: Draft, requested: StartupInput["count"], saved?: StartupAnswers): void {
  if (requested === undefined) return;
  if (draft.mode === "single") throw new Error("single 不接受子代理数量");
  const count = parseCount(requested);
  if (saved && count !== saved.count) throw new Error("同 Session 预算已锁定；扩容须显式 add-slot");
  draft.count = count;
}

function applyAudit(draft: Draft, input: StartupInput, saved?: StartupAnswers): void {
  for (const field of FIELDS) {
    const { key } = field;
    const value = input.audit?.[key];
    if (value === undefined) {
      if (input.defaults && !saved) setAuditField(draft, key, { value: field.fallback, source: "default" });
      continue;
    }
    if (!acceptsAuditValue(field, value)) throw new Error(`无效 ${key}`);
    if (saved) {
      if (saved.audit[key] !== value) throw new Error("同 Session 审计答案已确认；不能借新任务隐式覆盖");
      continue;
    }
    setAuditField(draft, key, { value, source: "explicit" });
  }
}

export async function collectStartup(
  context: ExtensionContext,
  input: StartupInput,
  { saved, current = () => {} }: StartupOptions = {},
): Promise<StartupAnswers> {
  const draft: Draft = saved ? structuredClone(saved) : { audit: { source: {} } };
  applyMode(draft, input.mode, saved);
  applyBudget(draft, input.count, saved);
  applyAudit(draft, input, saved);
  for (const question of STARTUP_QUESTIONS) await question.collect(draft, { context, current });
  draft.count = draft.mode === "single" ? 0 : (draft.count ?? 1);
  return validateAnswers(draft);
}

export function registerStartupFlags(pi: ExtensionAPI): void {
  pi.registerFlag("coding-mode", { description: "显式启用 single 或 multi", type: "string" });
  pi.registerFlag("coding-count", { description: "multi 的正整数预算；省略为1", type: "string" });
  pi.registerFlag("coding-audit-defaults", {
    description: "明确接受缺失审计字段的默认值",
    type: "boolean",
    default: false,
  });
  for (const field of FIELDS) {
    pi.registerFlag(field.flag, { description: `${field.key}: ${field.values.join(" | ")}`, type: "string" });
  }
}

export function startupFlags(pi: ExtensionAPI): StartupInput {
  return {
    mode: pi.getFlag("coding-mode") as string | undefined,
    count: pi.getFlag("coding-count") as string | undefined,
    defaults: pi.getFlag("coding-audit-defaults") === true,
    audit: Object.fromEntries(FIELDS.map((field) => [field.key, pi.getFlag(field.flag)])),
  };
}

interface CommandOptions extends StartupInput {
  audit: NonNullable<StartupInput["audit"]>;
}

function applyOption(input: CommandOptions, flag: string, value?: string): void {
  const auditField = FIELDS.find((field) => flag === `--${field.flag.slice(7)}`);
  if (!value || (!auditField && flag !== "--mode" && flag !== "--count")) {
    throw new Error(`无效启动参数 ${flag}`);
  }
  if (auditField) {
    input.audit[auditField.key] = value;
    return;
  }
  if (flag === "--mode") {
    if (input.mode) throw new Error("重复模式");
    input.mode = value;
    return;
  }
  if (input.count !== undefined) throw new Error("重复数量");
  input.count = value;
}

function parseOptions(rest: string, options: CommandOptions): string {
  const seen = new Set<string>();
  while (rest.startsWith("--")) {
    const [flag, value] = rest.split(/\s+/, 2);
    if (flag === "--") return rest.slice(2).trim();
    if (seen.has(flag)) throw new Error(`重复启动参数 ${flag}`);
    seen.add(flag);
    rest = rest.slice(flag.length).trim();
    if (flag === "--audit-defaults") {
      options.defaults = true;
      continue;
    }
    applyOption(options, flag, value);
    rest = rest.slice(value.length).trim();
  }
  return rest;
}

// 启动参数只出现于任务正文之前，遇到 -- 后的内容原样交给任务。
export function parseStartupCommand(input: string): StartupRequest | undefined {
  const match = /^(start|single|multi)(?:\s+|$)([\s\S]*)$/.exec(input);
  if (!match) return undefined;
  const [, route, request] = match;
  let rest = request.trim();
  const options: CommandOptions = { mode: route === "start" ? undefined : route, audit: {} };
  if (route !== "start" && /^[+-]?\d+(?:\.\d+)?(?:\s|$)/.test(rest)) {
    const [count] = rest.split(/\s/);
    options.count = count;
    rest = rest.slice(count.length).trim();
  }
  const task = parseOptions(rest, options);
  if (!task || task.length > 8000) throw new Error("启动任务必须明确且不超过8000字符");
  return { input: options, task };
}
