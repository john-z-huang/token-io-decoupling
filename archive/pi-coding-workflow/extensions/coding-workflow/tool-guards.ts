import { existsSync, realpathSync, statSync } from "node:fs";
import { dirname, relative, resolve, sep } from "node:path";
import { exactPath } from "./engine/workflow-execution.ts";
import type { ContentVerification, Dimension, Effect } from "./host/session-state.ts";

export const WORKFLOW_TOOL_NAMES = new Set([
  "coding_checkpoint",
  "coding_slice",
  "coding_run",
  "coding_delegate",
]);

export interface ToolIntent {
  effect: Effect;
  verification?: ContentVerification;
  delegate?: boolean;
}

export interface ToolCallState {
  intents: Map<string, ToolIntent>;
  allowedDelegates: Set<string>;
  observedMutations: Set<string>;
  releasedReservations: Set<string>;
  results: Map<string, string>;
}

export function affectsEpoch(effect: Effect): effect is Dimension {
  return effect === "content" || effect === "documentation" || effect === "git";
}

export function parentCallId(id: string): string | undefined {
  const separator = id.lastIndexOf("/");
  return separator < 0 ? undefined : id.slice(0, separator);
}

export function nearestIntent(intents: ToolCallState["intents"], id?: string): ToolIntent | undefined {
  while (id) {
    const intent = intents.get(id);
    if (intent) return intent;
    id = parentCallId(id);
  }
  return undefined;
}

function existingAncestor(target: string): string {
  // 新文件尚无法 realpath，先核对最近的现有祖先，覆盖目录符号链接。
  let ancestor = target;
  while (!existsSync(ancestor)) {
    const parent = dirname(ancestor);
    if (parent === ancestor) throw new Error("没有可核验的路径祖先");
    ancestor = parent;
  }
  return ancestor;
}

export function scopedPath(cwd: string, path: unknown): string {
  if (typeof path !== "string" || !path) throw new Error("缺少文件路径");
  const projectRoot = realpathSync(cwd);
  const target = resolve(projectRoot, path);
  const relativePath = relative(projectRoot, target).split(sep).join("/");
  if (!exactPath(relativePath)) throw new Error("路径须在当前项目内，且不能指向 .git 或目录");

  const ancestor = existingAncestor(target);
  const realAncestor = realpathSync(ancestor);
  if (realAncestor !== projectRoot && !realAncestor.startsWith(projectRoot + sep)) {
    throw new Error("路径穿过项目外符号链接");
  }
  if (existsSync(target) && statSync(target).isDirectory()) {
    throw new Error("Slice 只接受精确文件，不接受目录");
  }

  const canonicalTarget = resolve(realAncestor, relative(ancestor, target));
  const canonicalPath = relative(projectRoot, canonicalTarget).split(sep).join("/");
  if (!exactPath(canonicalPath)) throw new Error("规范目标路径不能指向 .git、项目外或通配范围");
  return canonicalPath;
}

export function fileEffect(path: string): "content" | "documentation" {
  return /\.(md|mdx|rst|txt|adoc)$/i.test(path) ? "documentation" : "content";
}
