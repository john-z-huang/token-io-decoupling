import { Type, type Static } from "typebox";
import { ROLES } from "./host/session-state.ts";

const text = (maxLength = 2000) => Type.String({ minLength: 1, maxLength });
const enumeration = <T extends string>(values: readonly T[]) =>
  Type.Union(values.map((value) => Type.Literal(value)));
const evidence = Type.Array(text(), { minItems: 1, maxItems: 16 });
const revision = Type.Integer({ minimum: 0 });
const effect = enumeration(["read", "check", "content", "documentation", "git", "memory"]);

const slice = Type.Object(
  {
    objective: text(),
    paths: Type.Array(text(4096), { maxItems: 64 }),
    mutations: Type.Array(effect, { minItems: 1, maxItems: 6 }),
    returnConditions: text(),
    unreleased: text(),
    evidence,
  },
  { additionalProperties: false },
);

const delegateJob = Type.Object(
  {
    role: enumeration(ROLES),
    agent: text(128),
    task: text(8000),
    paths: Type.Array(text(4096), { maxItems: 64 }),
    model: Type.Optional(
      Type.String({
        minLength: 5,
        maxLength: 256,
        description:
          "Root按任务与模型卡选择精确provider/model:thinking；Sol复杂编码，Terra视觉/文字，Luna聚焦高吞吐。推理档位按任务选择，不按角色固定。",
      }),
    ),
    modelReason: Type.Optional(text()),
  },
  { additionalProperties: false },
);

const checkpoint = Type.Union([
  Type.Object(
    {
      action: Type.Literal("status"),
      offset: Type.Optional(Type.Integer({ minimum: 0, maximum: 127 })),
    },
    { additionalProperties: false },
  ),
  Type.Object(
    {
      action: Type.Literal("rules"),
      document: Type.Optional(text(96)),
      fragment: Type.Optional(text(96)),
    },
    { additionalProperties: false },
  ),
  Type.Object(
    {
      action: Type.Literal("result"),
      resultId: text(),
      offset: Type.Optional(Type.Integer({ minimum: 0 })),
    },
    { additionalProperties: false },
  ),
  Type.Object({ action: Type.Literal("pause"), revision, reason: text() }, { additionalProperties: false }),
  Type.Object({ action: Type.Literal("resume"), revision, evidence }, { additionalProperties: false }),
  Type.Object(
    { action: Type.Literal("resolve_effect"), revision, callId: text(), evidence },
    { additionalProperties: false },
  ),
]);

export const workflowToolSchemas = {
  checkpoint,
  slice: Type.Object({ revision, slice }, { additionalProperties: false }),
  run: Type.Object(
    {
      revision,
      tool: text(),
      input: Type.Record(Type.String(), Type.Unknown()),
      effect,
      rationale: text(),
      evidence,
      verificationEvidence: Type.Optional(
        Type.Array(text(), {
          minItems: 1,
          maxItems: 16,
          description: "effect=git 时须给出当前内容和文档的成功检查回执 ID",
        }),
      ),
    },
    { additionalProperties: false },
  ),
  delegate: Type.Object(
    {
      revision,
      tool: text(),
      evidence,
      jobs: Type.Array(delegateJob, { minItems: 1, maxItems: 4 }),
    },
    { additionalProperties: false },
  ),
};

export type WorkflowToolSchemas = typeof workflowToolSchemas;
export type CheckpointInput = Static<typeof checkpoint>;
export type RunInput = Static<WorkflowToolSchemas["run"]>;
export type DelegateInput = Static<WorkflowToolSchemas["delegate"]>;
export type DelegateJob = Static<typeof delegateJob>;
