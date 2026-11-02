# Optimization benchmark

[English](OPTIMIZATION_BENCHMARK.md) | [简体中文](OPTIMIZATION_BENCHMARK_zh_cn.md)

This document owns the measurement method and observed results for the Issue #182 service-component benchmark. It does not define workflow authority, production configuration, or a full Agent cost model.

## Measurement boundary

The baseline reference caller receives full verified relevant facts; the assisted caller receives actual component results, verified facts, and the used tool's actual description and request-payload schema. Both arms have the same semantic objective and a frozen correctness oracle.

These are direct Python service-component measurements, not the current Root Agent's usage, a complete Agent session, MCP transport overhead, real host authorization, or monetary cost. Server initialization, unused-tool metadata, MCP envelopes/transport, fact gathering, and complete Agent reasoning are outside this comparison. API-call wall times exclude fixture setup; per-case elapsed time includes setup and local source/harness work. Overlapping sublayers must not be added together or treated as an end-to-end speedup.

The [fixed dataset](benchmarks/issue_182_cases.json) has data-format schema version 1 and evaluation protocol version 2:

| Case | Required semantic result |
| --- | --- |
| Bounded verification rules | Current Verification remains required; preflight cannot replace it. |
| Locked Multi-Agent stage advice | Ready entry/session and pending work definition map to the work-definition module; advice grants no authority. |
| Generic candidate preflight | A bounded new candidate with a trusted absent baseline passes applicable structural checks. |
| Skill language violation | The bilingual candidate with an invalid cross-language Related link is rejected. |
| Skill-instruction materialization | The approved fact Markdown reaches the exact expected file bytes through the selected path. |

The broader Single/Multi, missing-reader, permission, conflict, recovery, and epoch matrices remain in unit/integration tests. This small dataset is descriptive evidence, not a general workload estimate.

## Controls and correctness

Freeze case facts, prompts, output schemas, expected results, and source/metadata hashes before collection. Use an independent temporary project/state fixture for every case and arm. Changed source during collection invalidates comparison.

The materialization baseline returns approved file content for a bounded local harness write. The assisted arm uses actual prepare, same-manifest inspection, fresh whole-batch preflight, reauthorization/baseline checks, and exact application. A common oracle checks independently expected bytes and final filesystem state. The assisted StateService is real; host binding and operator grants are synthetic fixtures. The baseline harness does not use StateService. Neither proves production authorization.

Expected rejection is a correct negative result, not a completed file effect. Each case has its own closed answer domain: final-Verification requirements cannot substitute for structural-preflight status. File-effect completion comes from actual filesystem evidence, including exception paths, and is not a model-output scoring field; unreadable evidence remains unknown.

Record first-attempt correctness, bounded semantic repair, and final correctness separately. Allow at most one semantic repair per case/arm, no provider-error retries, no extra cases after collection, and no favorable reruns. A sequential run is capped at 30 transport attempts; remaining work after the cap is unrun.

The reference caller requests gpt-6-luna at medium effort, zero automatic retries, and at most 4,000 output tokens. Both nonblank process OPENAI_API_KEY and OPENAI_BASE_URL are explicitly used. Inner calls preserve production contracts: router timeout 20 seconds with no Decisions reasoning parameter; materializer timeout 30 seconds at medium effort. Record requested/reported settings where exposed, otherwise unknown. Never persist credentials, endpoint values, headers, or raw provider errors.

## Metrics and interpretation

Record API-reported input/output/total tokens separately for caller and inner requests. Missing/unexposed usage is null; explicit no-call paths have zero calls and null usage. Incomplete telemetry retains coverage and cannot masquerade as a complete aggregate.

Count logical API calls, actual HTTP attempts including failures, and component invocations separately. Argument/result UTF-8 bytes are not tokens. Fake tests validate mechanics only and never supply live measurements.

Report API, component, setup, harness, and apply timings separately. Baseline local writes and controlled apply are different paths. Compare caller tokens and caller-plus-inner tokens separately; reduced caller output may increase total input, tokens, or calls. Efficiency comparison requires current fingerprints, complete telemetry, and valid semantic results.

## Observed results

Protocol 2 ran on 2026-11-02, 15:49:32–15:50:09 UTC. Both arms passed 5/5 cases on the first attempt: 0/5 repairs and 0/5 failures each. All ten rows executed; source/dataset/metadata fingerprints stayed stable and all 12 API requests reported complete usage. Requested and reported model IDs were gpt-6-luna.

| Metric across five cases | Baseline | Assisted |
| --- | ---: | ---: |
| Caller input tokens | 11,028 | 12,930 |
| Caller output tokens | 859 | 544 |
| Caller total tokens | 11,887 | 13,474 |
| Inner input / output / total tokens | — (no call) | 2,874 / 43 / 2,917 |
| All API total tokens | 11,887 | 16,391 |
| Caller / inner API calls | 5 / 0 | 5 / 2 |
| Actual HTTP attempts | 5 | 7 |
| Caller API-call wall time | 17,119.916 ms | 14,943.883 ms |
| Inner API-call wall time | — (no call) | 4,113.276 ms |
| All API-call wall time | 17,119.916 ms | 19,057.159 ms |

Caller output fell 36.7%, while caller input rose 17.2% and all API tokens rose 37.9%. Calls increased from five to seven; summed API-call wall time rose 11.3%. This does not establish overall token savings or an end-to-end speedup. Metadata/schema and two inner requests are included; the small sample does not isolate or generalize their effects, and no pricing/cache-adjusted cost is claimed.

The assisted arm made seven direct component invocations: one rule lookup, one router, two preflights, and three materialization actions. Arguments totaled 2,978 UTF-8 bytes and results 14,732 bytes. The baseline file harness took 0.001273 seconds, controlled apply 0.009417 seconds, and assisted materialization setup 0.109502 seconds. These different apply paths are not an equivalent timing comparison. Full per-row/layer timing is retained.

The [protocol 2 raw report](benchmarks/issue_182_live_protocol2_2026-11-02.json) is the primary comparison. The [protocol 1 raw report](benchmarks/issue_182_live_2026-11-02.json) is audit-only: 15 requests, 7/10 scored rows, and three attempted repairs. Its shared outcome vocabulary mixed overlapping properties, so it cannot support quality or efficiency conclusions; its original comparison flag predates the semantic-validity gate. Exactly one protocol correction and complete rerun occurred. Facts, tasks, templates, expected bytes, model, effort, and budgets were preserved; no further runs were selected for favorable figures.

The [protocol 1 manifest](benchmarks/protocol_v1/manifest.json) binds its original [dataset](benchmarks/protocol_v1/issue_182_cases.json), [case source](benchmarks/protocol_v1/benchmark_cases.py.txt), [metrics source](benchmarks/protocol_v1/benchmark_metrics.py.txt), and [runner source](benchmarks/protocol_v1/optimization_benchmark.py.txt) to recorded hashes. Archived source text is reference data, not an execution entry point.

## Reproduction

Review the [runner](tests/support/optimization_benchmark.py) and [dataset](benchmarks/issue_182_cases.json). After authorizing real requests and configuring both process variables, run from mcp/ with an unused output path:

```sh
uv run --no-sync --package token-io-decoupling python tests/support/optimization_benchmark.py --live --output benchmarks/new_authorized_run.json
```

Without live opt-in, no measurement requests run. Existing output paths are rejected before API calls. Reproduction yields another descriptive sample, not a guarantee of these numbers. It does not use Codex SDK; the separate ordered final check owns fresh-CLI inspection.

## Related guides

- [Workflow routing](WORKFLOW_ROUTING.md)
- [Candidate compliance](CANDIDATE_COMPLIANCE.md)
- [Output materialization](OUTPUT_MATERIALIZATION.md)
