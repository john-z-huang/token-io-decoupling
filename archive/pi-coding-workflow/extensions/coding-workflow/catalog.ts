import { createHash } from "node:crypto";
import { readFileSync, readdirSync } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { loadReferenceData } from "./reference-data.ts";

export const RULES_ROOT = fileURLToPath(new URL("../../docs/rules/", import.meta.url));
export { headingSlug } from "./reference-data.ts";
export {
  documentLinks,
  mapDocumentLinks,
  resolveDocumentLink,
  resolveHookLink,
  rewriteDocumentLinks,
  rewriteWorkflowLinks,
  ruleLink,
} from "./rules/document-links.ts";
export const WORKFLOW_DIR = "coding-workflows";
const PHASES = [
  "entry",
  "session",
  "definition",
  "execution",
  "verification",
  "documentation",
  "delivery",
] as const;
export type Mode = "single" | "multi";
export const HOOK_IDS = [
  "foundation",
  "entry",
  "session",
  "planning",
  "execution",
  "delegation",
  "context",
  "audit",
  "verification",
  "repair",
  "documentation",
  "delivery",
  "recovery",
  "navigation",
  "advisory",
  "materialization",
] as const;
export type HookId = (typeof HOOK_IDS)[number];
const SEMANTIC_TRIGGERS = [
  "requirements_changed",
  "decision_required",
  "executor_changed",
  "repair_required",
  "documentation_impact",
  "git_changed",
  "context_exchange",
  "advice_requested",
  "materialization_requested",
  "capability_changed",
] as const;
const HOOK_TRIGGERS = [
  "workflow",
  ...PHASES,
  ...SEMANTIC_TRIGGERS,
  "multi_execution",
  "recovery_needed",
  "repair_review",
  "independent_verification",
  "active_allocation",
] as const;
export type HookTrigger = (typeof HOOK_TRIGGERS)[number];

export interface Catalog {
  root: string;
  routes: Record<Mode, string>;
  hookTriggers: Record<HookId, HookTrigger[]>;
  references: ReturnType<typeof loadReferenceData>;
  digest: string;
}

function readHookActivation(references: Catalog["references"], hook: HookId): HookTrigger[] {
  const activation = references.hookActivation(hook);
  if (
    !Array.isArray(activation) ||
    !activation.length ||
    new Set(activation).size !== activation.length ||
    activation.some((item) => !HOOK_TRIGGERS.includes(item))
  ) {
    throw new Error("Hook " + hook + " 的 activate_on 缺失或包含无效触发条件");
  }
  return activation;
}

export function loadCatalog(root = RULES_ROOT): Catalog {
  const references = loadReferenceData(root);
  const hash = createHash("sha256").update(references.digest);
  const directory = new URL("./", import.meta.url);
  for (const file of readdirSync(directory, { recursive: true, encoding: "utf8" })
    .filter((file) => file.endsWith(".ts"))
    .sort()) {
    hash.update(file).update(readFileSync(new URL(file, directory)));
  }
  const routes = { single: "coding-single-agent", multi: "coding-multi-agent" };
  for (const id of Object.values(routes)) references.document(id);
  const hookTriggers = {} as Catalog["hookTriggers"];
  for (const hook of HOOK_IDS) hookTriggers[hook] = readHookActivation(references, hook);
  return { root: resolve(root), routes, hookTriggers, references, digest: hash.digest("hex") };
}

export function hookDocument(id: HookId): string {
  return "hook-" + id;
}
