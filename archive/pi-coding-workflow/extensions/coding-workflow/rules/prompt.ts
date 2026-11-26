import {
  HOOK_IDS,
  rewriteWorkflowLinks,
  ruleLink,
  type Catalog,
  type HookId,
  type HookTrigger,
  type Mode,
} from "../catalog.ts";
import type { Workflow } from "../engine.ts";

export const MAX_CONTEXT = 96000;
const REQUIRED_HOOK_RULES: Partial<Record<HookId, string>> = {
  verification: "verification-epoch#actions",
};
export function renderFragment(catalog: Catalog, documentId: string, fragment: string): string {
  const document = catalog.references.document(documentId);
  const body = catalog.references.readFragment(document.id, fragment);
  return rewriteWorkflowLinks(catalog, document.path, body);
}

// 规则来源对照保留在链接文档中，避免把维护信息混入执行合同。
export function renderHook(catalog: Catalog, hook: HookId, mode: Mode): string {
  const template = rewriteWorkflowLinks(catalog, `hooks/${hook}.md`, catalog.references.readHook(hook));
  const required = REQUIRED_HOOK_RULES[hook];
  if (required && !template.split("\n").includes(`<!-- rule:${required} -->`)) {
    throw new Error(`Hook ${hook} 缺少必需规则片段：${required}`);
  }
  const body = template.replace(
    /^<!-- rule:([a-z][a-z0-9-]*)#([A-Za-z][A-Za-z0-9-]*) -->$/gm,
    (_marker, owner: string, fragment: string) => renderFragment(catalog, owner, fragment),
  );
  if (hook !== "entry") return `[Hook:${hook}]\n\n${body}`;

  const route = catalog.routes[mode];
  const modeBoundary = renderFragment(catalog, route, "mode-boundary");
  return `[Hook:${hook}]\n\n${body}\n\n## 当前路线的 Mode 边界\n\n${modeBoundary}`;
}

export function renderContext({ catalog, state }: Workflow): string {
  const route = catalog.routes[state.mode];
  const path = catalog.references.document(route).path;
  const instructions = rewriteWorkflowLinks(catalog, path, catalog.references.readRoute(route));
  const triggers = new Set<HookTrigger>(["workflow"]);
  if (state.capabilityChanged) triggers.add("capability_changed");
  if (state.status === "paused" || state.inFlight.length) triggers.add("recovery_needed");
  if (state.allocations.some(({ status }) => status === "running" || status === "uncertain")) {
    triggers.add("active_allocation");
  }
  const hooks = HOOK_IDS.filter((id) => catalog.hookTriggers[id].some((trigger) => triggers.has(trigger)));
  const context = [
    "[Coding Hooks] 按 YAML 路线和当前证据自行推进。阶段和适用性由你判断，完成各项工作后直接向用户汇报。",
    "遇到对应动作或语义变化时读取适用 Hook。用 coding_checkpoint rules 查询 document/fragment，省略 fragment 可读取 Hook 正文及目录。范围、执行者或能力变化后须重核并放行新的 Slice。",
    "受约束写入前使用 coding_slice。Bash、codemode、MCP 等不透明调用走 coding_run，委派走 coding_delegate。工具回执只证明可观察事实，授权及验证充分性由你核对。",
    "按验证和交付合同核对实际结果。Git 调用在 coding_run.verificationEvidence 引用当前内容和文档的检查回执。",
    "Hook 触发目录：" + ruleLink("hook-readme"),
    instructions,
    ...hooks.map((id) => renderHook(catalog, id, state.mode)),
    JSON.stringify({
      mode: state.mode,
      status: state.status,
      reason: state.reason,
      audit: state.audit,
      revision: state.revision,
      epoch: state.epoch,
      slice: state.slice,
      recoveryHint: state.recoveryHint,
      inFlight: state.inFlight,
      childCount: state.childCount,
      allocations: state.allocations,
      observations: state.observations.slice(-24),
    }),
  ].join("\n\n");
  if (context.length > MAX_CONTEXT) throw new Error("Coding 上下文超出96000字符上限，不能截断守卫合同");
  return context;
}
