import assert from 'node:assert/strict';
import { loadCatalog } from '../extensions/coding-workflow/catalog.ts';
import { installWorkflow } from '../extensions/coding-workflow/runtime.ts';

export const catalog = loadCatalog();

export const callsSchema = {
  type: 'object',
  properties: {
    calls: {
      type: 'array',
      minItems: 1,
      maxItems: 8,
      items: {
        type: 'object',
        properties: {
          agent: { type: 'string' },
          prompt: { type: 'string' },
          cwd: { type: 'string' },
          initialContext: { type: 'string', enum: ['empty', 'parent'] },
          model: { type: 'string' },
          thinking: { type: 'string', enum: ['off', 'minimal', 'low', 'medium', 'high', 'xhigh', 'max'] },
          session: { type: 'string' },
        },
        required: ['agent', 'prompt'],
      },
    },
  },
  required: ['calls'],
};

export function body(text) {
  return { content: [{ type: 'text', text }], details: {} };
}

function syntheticTools() {
  return new Map([
    ['read', { parameters: {}, execute: async () => body('actual synthetic readback') }],
    ['write', { parameters: {}, execute: async () => body('synthetic write result') }],
    ['bash', { parameters: {}, execute: async () => body('synthetic command result') }],
    [
      'subagent',
      {
        parameters: structuredClone(callsSchema),
        execute: async () => body('actual synthetic task result with paths/checks/failures'),
      },
    ],
  ]);
}

function createPi(host) {
  const { handlers, definitions, commands, flags, entries, messages, raw } = host;
  return {
    on(name, handler) {
      const listeners = handlers.get(name) ?? [];
      listeners.push(handler);
      handlers.set(name, listeners);
    },
    registerFlag() {},
    getFlag: (name) => flags[name],
    registerTool: (definition) => definitions.set(definition.name, definition),
    registerCommand: (name, definition) => commands.set(name, definition),
    appendEntry(customType, data) {
      entries.push({
        id: `entry-${++host.sequence}`,
        type: 'custom',
        customType,
        data: structuredClone(data),
      });
    },
    sendMessage: (message, opts) => messages.push({ message, opts }),
    getAllTools: () =>
      [...raw].map(([name, { parameters, annotations }]) => ({ name, parameters, annotations })),
  };
}

function createContext(entries, options) {
  let branch;
  let sessionId = 'runtime-test';
  const ctx = {
    cwd: process.cwd(),
    hasUI: options.hasUI ?? false,
    ui: { select: options.select, input: options.input, notify() {}, setStatus() {} },
    sessionManager: {
      getSessionId: () => sessionId,
      getEntries: () => entries,
      getBranch: () => branch ?? entries,
    },
  };
  return {
    ctx,
    setBranch(value) {
      branch = value;
    },
    setSessionId(value) {
      sessionId = value;
    },
  };
}

async function executeRegisteredTool(host, call, { ctx, invoke }) {
  const { id, name, input } = call;
  try {
    const definition = host.definitions.get(name) ?? host.raw.get(name);
    if (!definition) throw new Error('Unknown tool');
    host.calls.push(call);
    let nestedCalls = 0;
    const tools = [...host.raw].filter(([, spec]) => !spec.hidden).map(([name, spec]) => ({ ...spec, name }));
    const toolContext = {
      ...ctx,
      tools,
      executeTool: (target, args) =>
        invoke(target, args, { id: `${id}/${++nestedCalls}`, parentToolCallId: id }),
    };
    const result = await definition.execute(id, input, undefined, undefined, toolContext);
    return { result, isError: result.isError === true, durationMs: 1 };
  } catch (error) {
    return { result: body(String(error)), isError: true, durationMs: 1 };
  }
}

function createDispatcher(host, ctx) {
  async function emit(name, event = {}) {
    let output;
    for (const handler of host.handlers.get(name) ?? []) {
      output = (await handler({ type: name, ...event }, ctx)) ?? output;
    }
    return output;
  }

  async function invoke(name, input, { id = `call-${++host.sequence}`, parentToolCallId } = {}) {
    const event = { toolName: name, toolCallId: id, parentToolCallId };
    const decision = await emit('tool_call', { ...event, input });
    // 被 Hook 阻止的调用不带运行时长，扩展据此区分失败与实际未运行。
    const outcome = decision?.block
      ? { result: body(decision.reason), isError: true, durationMs: undefined }
      : await executeRegisteredTool(host, { name, input, id, parentToolCallId }, { ctx, invoke });
    await emit('tool_execution_end', { ...event, ...outcome });
    return { toolCall: { id, name, arguments: input }, ...outcome };
  }

  return { emit, invoke };
}

function createActions({ commands, ctx, invoke, messages, w }) {
  const userRef = () => w().state.observations.find((observation) => observation.effect === 'user').id;
  function run(tool = 'bash', effect = 'read', input = {}, verificationEvidence) {
    return invoke('coding_run', {
      revision: w().state.revision,
      tool,
      input,
      effect,
      rationale: '合成测试中已明确该实际调用的影响范围',
      evidence: [userRef()],
      verificationEvidence,
    });
  }
  async function start(args = 'single 合成任务，用户明确禁止持久化计划') {
    const command = args.replace(/^(single|multi)(\s+\d+)?\s+/, '$1$2 --audit-defaults ');
    await commands.get('coding').handler(command, ctx);
    assert.ok(w(), messages.at(-1)?.message.content);
  }
  return { userRef, run, start };
}

export function harness(options = {}) {
  const host = {
    handlers: new Map(),
    definitions: new Map(),
    commands: new Map(),
    entries: structuredClone(options.entries ?? []),
    messages: [],
    calls: [],
    flags: options.flags ?? {},
    sequence: 0,
    raw: syntheticTools(),
  };
  const pi = createPi(host);
  const session = createContext(host.entries, options);
  // Schema 校验由真实 Pi 的入口 smoke 覆盖，这里模拟宿主事件和调用结果。
  const installed = installWorkflow(
    pi,
    { checkpoint: {}, slice: {}, run: {}, delegate: {} },
    options.catalog ?? catalog,
  );
  const fixture = {
    ...installed,
    ...session,
    ...createDispatcher(host, session.ctx),
    w: installed.getWorkflow,
    pi,
    raw: host.raw,
    definitions: host.definitions,
    commands: host.commands,
    entries: host.entries,
    messages: host.messages,
    calls: host.calls,
  };
  return { ...fixture, ...createActions(fixture) };
}

export async function releaseSlice(
  host,
  { paths = ['synthetic.ts'], mutations = ['content', 'documentation'] } = {},
) {
  const result = await host.invoke('coding_slice', {
    revision: host.w().state.revision,
    slice: {
      objective: 'synthetic scoped task',
      paths,
      mutations,
      returnConditions: 'return evidence',
      unreleased: 'network and unrelated paths',
      evidence: [host.userRef()],
    },
  });
  assert.equal(result.isError, false, result.result.content[0].text);
}
