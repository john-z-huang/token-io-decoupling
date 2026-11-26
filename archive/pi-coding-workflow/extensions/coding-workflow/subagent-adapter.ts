/** 适配宿主工具的 Schema，预算和授权由调用方核验。 */
import { parseModelSelection, validateChildSelection } from "./model-selection.ts";

interface Schema {
  type?: string;
  properties?: Record<string, Schema>;
  required?: string[];
  items?: Schema;
  minItems?: number;
  maxItems?: number;
  enum?: unknown[];
  const?: unknown;
}
export interface SubagentAdapter {
  fields: Record<string, Schema>;
}

interface ObjectSchema extends Schema {
  type: "object";
  properties: Record<string, Schema>;
}

function object(value: unknown): ObjectSchema | undefined {
  if (!value || typeof value !== "object" || Array.isArray(value)) return undefined;
  const schema = value as Schema;
  return hasObjectFields(schema) ? schema : undefined;
}

function hasObjectFields(schema: Schema): schema is ObjectSchema {
  const { properties } = schema;
  return (
    schema.type === "object" &&
    Boolean(properties) &&
    typeof properties === "object" &&
    !Array.isArray(properties)
  );
}
function requiredWithin(schema: Schema, names: string[]): boolean {
  return (
    schema.required === undefined ||
    (Array.isArray(schema.required) && schema.required.every((name) => names.includes(name)))
  );
}
function acceptsString(schema: Schema | undefined, value?: string): boolean {
  return (
    schema?.type === "string" &&
    (value === undefined ||
      ((schema.enum === undefined || (Array.isArray(schema.enum) && schema.enum.includes(value))) &&
        (schema.const === undefined || schema.const === value)))
  );
}

function acceptsSingleCall(calls: Schema | undefined): calls is Schema {
  if (!calls || calls.type !== "array") return false;
  if ((calls.minItems ?? 0) > 1 || (calls.maxItems ?? 1) < 1) return false;
  return true;
}

export function resolveSubagentAdapter(parameters: unknown): SubagentAdapter | undefined {
  const top = object(parameters);
  if (!top) return undefined;
  const { calls } = top.properties;
  if (!acceptsSingleCall(calls) || !requiredWithin(top, ["calls"])) return undefined;
  const item = object(calls.items);
  if (!item || !requiredWithin(item, ["agent", "prompt", "cwd", "initialContext"])) return undefined;
  const fields = item.properties;
  if (
    !["agent", "prompt", "cwd"].every((name) => acceptsString(fields[name])) ||
    !acceptsString(fields.initialContext, "empty")
  ) {
    return undefined;
  }
  return { fields };
}

export function compatibleSubagent(parameters: unknown): boolean {
  return !!resolveSubagentAdapter(parameters);
}

/** 整批任务在预留名额前核验模型参数，避免边执行边发现 Schema 不兼容。 */
export function subagentModelInput(adapter: SubagentAdapter, model?: string): Record<string, string> {
  if (model === undefined) return {};
  validateChildSelection(model);
  const { provider, id, thinking } = parseModelSelection(model);
  const selected = `${provider}/${id}`;
  if (!acceptsString(adapter.fields.model, selected) || !acceptsString(adapter.fields.thinking, thinking))
    throw new Error("calls[] 显式选型须有真实 model/thinking 字段及受支持档位；不静默忽略或回退");
  // pi-subagent 3.1.0 独立处理 thinking，单次调用优先于代理配置和启动值。
  return { model: selected, thinking };
}
interface SubagentCall {
  agent: string;
  task: string;
  cwd: string;
  modelInput: Record<string, string>;
}

export function subagentInput(call: SubagentCall): Record<string, unknown> {
  const { agent, task, cwd, modelInput } = call;
  return { calls: [{ agent, prompt: task, cwd, initialContext: "empty", ...modelInput }] };
}
