#!/usr/bin/env python3
"""Validate bilingual Layer-04 route/module maps and their checklists."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote

from workflow_module_contracts import L3_REQUIRED_LAYER12_LINK, MANIFEST_ROUTE_SHA256, MIXED_STEP_CONTRACTS, MODULES, MODULE_CHECKPOINTS, MODULE_CHECKPOINT_L3_OWNERS, MODULE_CHECKPOINT_LAYER12_TARGETS, MODULE_GRAPH_SHA256, MODULE_PREFIXES, MODULES_DIR, MODULE_REQUIRED_EDGES, MODULE_REQUIRED_EDGE_LABELS, MODULE_REQUIRED_LABEL_FRAGMENTS, MIGRATION_MANIFEST, MODULE_SEMANTIC_FRAGMENTS, ROUTE_MODULES, ROUTES_DIR, TOP_PREFIXES, VERIFICATION_STEP_CONTRACTS

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = Path(".github/workflows/multilingual-docs.yml")
SCRIPT = "scripts/check-layer-04-workflow-maps.py"
TEST = "tests/test_check_layer_04_workflow_maps.py"
MAP_HEADERS = {"en": "## Workflow map", "zh": "## 工作流路线图"}
LIST_HEADERS = {"en": "## Ordered module checklist", "zh": "## 有序模块清单"}
ROUTE_LIST_HEADERS = {"en": "## Ordered route checklist", "zh": "## 路线顺序检查清单"}
FENCE = re.compile(r"```mermaid\s*\n(.*?)\n```", re.S)
NODE = re.compile(r"^\s*([A-Z][A-Z0-9_]*)\s*[\[({]", re.M)
EDGE = re.compile(r"^\s*([A-Z][A-Z0-9_]*)\s*(?:--\s*(.*?)\s*-->|-->)\s*([A-Z][A-Z0-9_]*)\s*$", re.M)
STEP = re.compile(r"(?m)^(\d+)\.\s+\*\*([A-Z]+\d{2}) —")
LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
FENCED_CODE = re.compile(r"```[^\n]*\n.*?\n```", re.S)
INLINE_CODE_SPAN = re.compile(r"(`+)(.*?)\1", re.S)


def linked_paths(text: str) -> set[str]:
    operational = INLINE_CODE_SPAN.sub("", FENCED_CODE.sub("", text))
    return {unquote(raw.split("#", 1)[0].split("?", 1)[0]) for raw in LINK.findall(operational)}


def fail(errors: list[str], path: Path, message: str) -> None:
    errors.append(f"{path}: {message}")


def get_section(text: str, header: str) -> str | None:
    lines = text.splitlines()
    if lines.count(header) != 1:
        return None
    start = lines.index(header) + 1
    end = next((i for i in range(start, len(lines)) if lines[i].startswith("## ")), len(lines))
    return "\n".join(lines[start:end])


def parse_diagram(text: str, path: Path, lang: str, errors: list[str]):
    section = get_section(text, MAP_HEADERS[lang])
    if section is None:
        fail(errors, path, f"expected exactly one {MAP_HEADERS[lang]}")
        return {}, set(), {}, ""
    diagrams = FENCE.findall(section)
    if len(diagrams) != 1:
        fail(errors, path, "expected exactly one mermaid flowchart")
        return {}, set(), {}, ""
    raw = diagrams[0]
    declarations = NODE.findall(raw)
    if len(declarations) != len(set(declarations)):
        fail(errors, path, "duplicate map node ID")
    labels: dict[str, str] = {}
    for line in raw.splitlines():
        match = re.match(r"^\s*([A-Z][A-Z0-9_]*)\s*[\[({](.*?)[\])}]\s*$", line)
        if match:
            labels[match.group(1)] = match.group(2)
    edges = {(m.group(1), m.group(3)) for m in EDGE.finditer(raw)}
    for source, target in edges:
        if source not in declarations or target not in declarations:
            fail(errors, path, f"edge references undeclared node {source} -> {target}")
    return labels, edges, {node: set() for node in declarations}, raw


def graph_checks(path: Path, lang: str, labels: dict[str, str], edges: set[tuple[str, str]], raw: str, start: str, errors: list[str], final_checkpoint: str | None = None, require_skip: bool = True) -> None:
    nodes = set(labels)
    if start not in nodes:
        fail(errors, path, f"missing map entry checkpoint {start}")
        return
    adjacency = {node: set() for node in nodes}
    for source, target in edges:
        adjacency.setdefault(source, set()).add(target)
    reached = set()
    pending = [start]
    while pending:
        node = pending.pop()
        if node in reached:
            continue
        reached.add(node)
        pending.extend(adjacency.get(node, set()) - reached)
    for node in sorted(nodes - reached):
        fail(errors, path, f"orphan/unreachable map node {node}")
    for node, label in labels.items():
        terminal_label = re.fullmatch(r"\s*(?:complete|blocked)\s*", label, re.I)
        terminal_id = node in {"BLOCK", "DONE"} or node.endswith(("_BLOCK", "_DONE"))
        if (terminal_label or terminal_id) and adjacency.get(node):
            fail(errors, path, f"terminal node {node} has outgoing edges")
    if not any(node == "BLOCK" or node.endswith("_BLOCK") or re.fullmatch(r"\s*blocked\s*", label, re.I) for node, label in labels.items()):
        fail(errors, path, "map lacks explicit blocked result")
    complete_node = (any(node == "DONE" or node.endswith("_DONE") or re.fullmatch(r"\s*complete\s*", label, re.I) for node, label in labels.items())
                    or (final_checkpoint is not None and not adjacency.get(final_checkpoint)))
    if not complete_node and final_checkpoint is None:
        fail(errors, path, "map lacks explicit complete result")
    if not any("needs_prerequisite" in label for label in labels.values()):
        fail(errors, path, "map lacks explicit needs_prerequisite return")
    if require_skip and not re.search(r"not_applicable|\bN/?A\b|不适用", raw, re.I):
        fail(errors, path, "map lacks explicit conditional skip/not_applicable result")


def module_checkpoint_ids(text: str, path: Path, lang: str, errors: list[str]) -> list[str]:
    title = LIST_HEADERS[lang]
    section = get_section(text, title)
    if section is None:
        fail(errors, path, f"expected exactly one {title}")
        return []
    matches = list(STEP.finditer(section))
    numbers = [int(m.group(1)) for m in matches]
    if numbers != list(range(1, len(matches) + 1)):
        fail(errors, path, "module checklist numbering is not contiguous from 1")
    ids = [m.group(2) for m in matches]
    if len(ids) != len(set(ids)):
        fail(errors, path, "duplicate checklist checkpoint ID")
    return ids


def graph_fingerprint(labels: dict[str, str], raw: str) -> str:
    declared = [(match.group(1), labels.get(match.group(1), "")) for match in NODE.finditer(raw)]
    edges = [(match.group(1), match.group(2) or "", match.group(3)) for match in EDGE.finditer(raw)]
    payload = "\n".join(
        [f"N {node} {label}" for node, label in sorted(declared)]
        + [f"E {source} {label} {target}" for source, label, target in sorted(edges)]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def check_module(root: Path, module: str, lang: str, errors: list[str]):
    suffix = "_zh_cn" if lang == "zh" else ""
    path = root / MODULES_DIR / f"{module}{suffix}.md"
    if not path.is_file():
        errors.append(f"missing module map/checklist: {path}")
        return None
    text = path.read_text(encoding="utf-8")
    ids = module_checkpoint_ids(text, path, lang, errors)
    labels, edges, _, raw = parse_diagram(text, path, lang, errors)
    prefix = MODULE_PREFIXES[module]
    expected_ids = list(MODULE_CHECKPOINTS[module])
    if ids != expected_ids:
        fail(errors, path, f"module checklist must use the fixed ordered checkpoints {expected_ids}")
    if len(ids) != len(set(ids)):
        fail(errors, path, "checkpoint IDs are not unique")
    for checkpoint in ids:
        if checkpoint not in labels:
            fail(errors, path, f"checklist checkpoint missing from map: {checkpoint}")
    for source, target in MODULE_REQUIRED_EDGES[module]:
        if (source, target) not in edges:
            fail(errors, path, f"required module safety edge is missing: {source} -> {target}")
    for node, fragment in MODULE_REQUIRED_LABEL_FRAGMENTS.get(module, {}).get(lang, {}).items():
        if fragment not in labels.get(node, ""):
            fail(errors, path, f"{node} is missing required safety label: {fragment}")
    for (source, target), fragment in MODULE_REQUIRED_EDGE_LABELS.get(module, {}).get(lang, {}).items():
        edge_label = next((match.group(2) or "" for match in EDGE.finditer(raw)
                           if (match.group(1), match.group(3)) == (source, target)), None)
        if edge_label is None or (fragment and fragment not in edge_label):
            fail(errors, path, f"required safety edge label is missing or weakened: {source} -> {target} ({fragment})")
    for checkpoint in labels:
        if checkpoint.startswith(prefix) and re.fullmatch(prefix + r"\d{2}", checkpoint) and checkpoint not in ids:
            fail(errors, path, f"map checkpoint is absent from checklist: {checkpoint}")
    graph_checks(path, lang, labels, edges, raw, ids[0] if ids else "", errors,
                 final_checkpoint=ids[-1] if ids else None)
    if graph_fingerprint(labels, raw) != MODULE_GRAPH_SHA256[lang][module]:
        fail(errors, path, "map nodes, critical labels, and directed branch edges differ from the fixed module contract")
    if lang == "en":
        for fragment in MODULE_SEMANTIC_FRAGMENTS.get(module, ()):
            if fragment not in text:
                fail(errors, path, f"module lost required semantic contract: {fragment}")
    if ids and not re.search(r"complete|完成", get_section(text, LIST_HEADERS[lang]) or "", re.I):
        fail(errors, path, "final module checkpoint must define its completion result")
    # All modules resolve their own entry prerequisites first; all results must return, skip, complete, or block.
    step_section = get_section(text, LIST_HEADERS[lang]) or ""
    if not re.search(r"module-entry-resolution|模块入口解析", step_section, re.I):
        fail(errors, path, "numbered entry step does not consume module-entry-resolution")
    if "needs_prerequisite" not in raw:
        fail(errors, path, "map has no needs_prerequisite node")
    return ids, labels, edges, raw, text


def check_route(root: Path, route: str, lang: str, errors: list[str]):
    suffix = "_zh_cn" if lang == "zh" else ""
    path = root / ROUTES_DIR / f"{route}{suffix}.md"
    if not path.is_file():
        errors.append(f"missing route map/checklist: {path}")
        return None
    text = path.read_text(encoding="utf-8")
    title = ROUTE_LIST_HEADERS[lang]
    checklist = get_section(text, title)
    if checklist is None:
        fail(errors, path, f"expected exactly one {title}")
        checklist = ""
    matches = list(STEP.finditer(checklist))
    prefix = TOP_PREFIXES[route]
    expected_ids = [f"{prefix}{i:02d}" for i in range(1, 8)]
    ids = [m.group(2) for m in matches]
    if [int(m.group(1)) for m in matches] != list(range(1, 8)) or ids != expected_ids:
        fail(errors, path, f"route checklist must have exactly ordered checkpoints {expected_ids}")
    expected_modules = ROUTE_MODULES[route]
    for i, match in enumerate(matches[:len(expected_modules)]):
        step_text = checklist[match.start():matches[i + 1].start() if i + 1 < len(matches) else len(checklist)]
        target = f"modules/{expected_modules[i]}{suffix}.md"
        if target not in linked_paths(step_text):
            fail(errors, path, f"{expected_ids[i]} must call its exact same-language module {target}")
    labels, edges, _, raw = parse_diagram(text, path, lang, errors)
    for checkpoint in expected_ids:
        if checkpoint not in labels:
            fail(errors, path, f"route checkpoint missing from map: {checkpoint}")
    forbidden = "DE" if route == "coding-single-agent" else None
    if forbidden and re.search(r"\bDE\d{2}\b|Child Creation|Child Dispatch|Worker Memo|子代理创建|子代理派发", raw):
        fail(errors, path, "Single-Agent route map contains delegated-execution branch")
    graph_checks(path, lang, labels, edges, raw, expected_ids[0], errors, require_skip=False)
    allowed = {(expected_ids[i], expected_ids[i + 1]) for i in range(6)}
    allowed.update({(expected_ids[4], expected_ids[4]), (expected_ids[5], expected_ids[4]),
                    (expected_ids[6], "DONE"), ("NEEDS", "RESUME"), ("NEEDS", "BLOCK"),
                    ("RESUME", "BLOCK"), ("ROUTE_ENTRY", "RESUME"), ("ROUTE_ENTRY", "BLOCK"),
                    (expected_ids[1], "ROUTE_ENTRY"), (expected_ids[2], "ROUTE_ENTRY")})
    allowed.update((f"{prefix}{i:02d}", target) for i in range(1, 8) for target in ("NEEDS", "BLOCK"))
    allowed.update(("RESUME", checkpoint) for checkpoint in expected_ids)
    for edge in edges - allowed:
        fail(errors, path, f"unexpected route edge {edge[0]} -> {edge[1]}; possible gate bypass")
    for edge in allowed - edges:
        # These main-chain/continuation edges are required; outcome edges are conditional but still required.
        if edge[0] in expected_ids or edge in {("NEEDS", "RESUME"), ("NEEDS", "BLOCK"), ("RESUME", "BLOCK"), ("ROUTE_ENTRY", "RESUME"), ("ROUTE_ENTRY", "BLOCK")}:
            fail(errors, path, f"required route edge {edge[0]} -> {edge[1]} is missing")
    if not re.search(r"ROUTE_ENTRY\s+--\s+[^\n]*resume original suspended caller[^\n]*-->\s+RESUME", raw, re.I) and lang == "en":
        fail(errors, path, "Route Entry must return to the original suspended caller")
    if lang == "zh" and not re.search(r"ROUTE_ENTRY\s+--\s+[^\n]*恢复原挂起调用位置[^\n]*-->\s+RESUME", raw):
        fail(errors, path, "Route Entry must return to the original suspended caller")
    for checkpoint in expected_ids:
        guard = "recorded caller is" if lang == "en" else "记录目标为"
        if not re.search(rf"RESUME\s+--\s+[^\n]*{re.escape(guard)}[^\n]*{checkpoint}[^\n]*-->\s+{checkpoint}", raw, re.I):
            fail(errors, path, f"RESUME must have guarded recorded-target return for {checkpoint}")
    if not re.search(r"RESUME\s+--\s+[^\n]*(?:record missing|conflicts|记录缺失|冲突)[^\n]*-->\s+BLOCK", raw, re.I):
        fail(errors, path, "missing/conflicting continuation record must block")
    return labels, edges


def check_repository(root: Path) -> list[str]:
    errors: list[str] = []
    route_pairs: dict[str, tuple[set[str], set[tuple[str, str]]]] = {}
    for route in ROUTE_MODULES:
        en = check_route(root, route, "en", errors)
        zh = check_route(root, route, "zh", errors)
        if en and zh:
            if (set(en[0]), en[1]) != (set(zh[0]), zh[1]):
                fail(errors, root / ROUTES_DIR / f"{route}.md", "English/Chinese route map topology differs")
            route_pairs[route] = (set(en[0]), en[1])
    for module in MODULES:
        en = check_module(root, module, "en", errors)
        zh = check_module(root, module, "zh", errors)
        if en and zh and (set(en[1]), en[2]) != (set(zh[1]), zh[2]):
            fail(errors, root / MODULES_DIR / f"{module}.md", "English/Chinese module map topology differs")
    for policy in ("AGENTS.md", "AGENTS_zh_cn.md"):
        path = root / policy
        if not path.is_file() or SCRIPT not in path.read_text(encoding="utf-8"):
            errors.append(f"{path}: missing map validator rule/command")
    validate_migration_manifest(root, errors)
    workflow_path = root / WORKFLOW
    if not workflow_path.is_file():
        errors.append(f"missing CI workflow: {workflow_path}")
    else:
        ci = workflow_path.read_text(encoding="utf-8")
        for required in (SCRIPT, TEST, f"python3 {SCRIPT}", f"python3 -m unittest discover -s tests -p '{Path(TEST).name}'"):
            if required not in ci:
                fail(errors, workflow_path, f"missing trigger or command {required}")
    return errors


def validate_migration_manifest(root: Path, errors: list[str]) -> None:
    path = root / MIGRATION_MANIFEST
    if not path.is_file():
        errors.append(f"missing development coverage manifest: {path}")
        return
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        fail(errors, path, f"invalid JSON: {exc}")
        return
    if data.get("schema_version") != 1 or data.get("baseline_commit") != "675627dc":
        fail(errors, path, "schema_version/baseline_commit mismatch")
    routes = data.get("routes", {})
    expected_steps = {"single-agent": [f"S{i:02d}" for i in range(1, 15)],
                      "multi-agent": [f"M{i:02d}" for i in range(1, 17)]}
    for route, source_steps in expected_steps.items():
        route_data = routes.get(route, {})
        entries = route_data.get("steps", [])
        fingerprint = hashlib.sha256(json.dumps(entries, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
        if fingerprint != MANIFEST_ROUTE_SHA256[route]:
            fail(errors, path, f"{route}: migration coverage differs from the fixed semantic mapping contract")
        ids = [entry.get("source_step") for entry in entries]
        if ids != source_steps:
            fail(errors, path, f"{route} must map every legacy step in order: {source_steps}")
        allowed_modules = set(ROUTE_MODULES[f"coding-{route}"])
        for entry in entries:
            mixed_contract = MIXED_STEP_CONTRACTS.get((route, entry.get("source_step")))
            if mixed_contract:
                if tuple(entry.get("semantic_substeps", [])) != mixed_contract["semantic_substeps"]:
                    fail(errors, path, f"{route}/{entry.get('source_step')}: fixed mixed-step semantic substeps/order changed")
                actual_sequence = tuple((target.get("module"), tuple(target.get("checkpoints", []))) for target in entry.get("targets", []))
                if actual_sequence != mixed_contract["target_sequence"]:
                    fail(errors, path, f"{route}/{entry.get('source_step')}: fixed mixed-step checkpoint call order/targets changed")
                if entry.get("branch_or_return") != mixed_contract["branch_or_return"]:
                    fail(errors, path, f"{route}/{entry.get('source_step')}: fixed branch/return distinction changed")
            verification_contract = VERIFICATION_STEP_CONTRACTS.get((route, entry.get("source_step")))
            if verification_contract:
                actual_checkpoints = tuple(cp for target in entry.get("targets", []) for cp in target.get("checkpoints", []))
                if actual_checkpoints != verification_contract["checkpoints"]:
                    fail(errors, path, f"{route}/{entry.get('source_step')}: current passing Verification must pass through VR06")
                if entry.get("branch_or_return") != verification_contract["return"]:
                    fail(errors, path, f"{route}/{entry.get('source_step')}: current Verification return result is missing or altered")
            if not entry.get("semantic_substeps") or not entry.get("targets"):
                fail(errors, path, f"{route}/{entry.get('source_step')}: semantic substeps/targets required")
            if not entry.get("branch_or_return"):
                fail(errors, path, f"{route}/{entry.get('source_step')}: branch/return description required")
            orders = [target.get("call_order") for target in entry.get("targets", [])]
            if orders != list(range(1, len(orders) + 1)):
                fail(errors, path, f"{route}/{entry.get('source_step')}: target call_order must be contiguous")
            for target in entry.get("targets", []):
                module = target.get("module")
                if module not in allowed_modules:
                    fail(errors, path, f"{route}/{entry.get('source_step')}: unauthorized target module {module}")
                    continue
                if target.get("consumption") not in {"direct", "transitive"}:
                    fail(errors, path, f"{route}/{entry.get('source_step')}: consumption must be direct/transitive")
                checkpoints = target.get("checkpoints", [])
                refs = target.get("owner_refs", [])
                expected_refs = sorted({owner for checkpoint in checkpoints
                                        for owner in MODULE_CHECKPOINT_L3_OWNERS.get(module, {}).get(checkpoint, set())})
                if sorted(refs) != expected_refs:
                    fail(errors, path, f"{route}/{entry.get('source_step')}: owner_refs must match owners consumed at the designated checkpoints: {expected_refs}")
                for lang, suffix in (("en", ""), ("zh", "_zh_cn")):
                    module_path = root / MODULES_DIR / f"{module}{suffix}.md"
                    if not module_path.is_file():
                        fail(errors, path, f"missing same-language target module: {module_path}")
                        continue
                    module_text = module_path.read_text(encoding="utf-8")
                    module_section = get_section(module_text, LIST_HEADERS[lang]) or ""
                    step_matches = list(STEP.finditer(module_section))
                    module_steps = {
                        match.group(2): module_section[match.start():step_matches[i + 1].start() if i + 1 < len(step_matches) else len(module_section)]
                        for i, match in enumerate(step_matches)
                    }
                    if not checkpoints or any(checkpoint not in module_steps for checkpoint in checkpoints):
                        fail(errors, path, f"{route}/{entry.get('source_step')}: target checkpoint missing from {module}{suffix} numbered checklist")
                        continue
                    fixed_direct_links = []
                    for checkpoint in checkpoints:
                        required_layer12 = MODULE_CHECKPOINT_LAYER12_TARGETS.get(module, {}).get(checkpoint)
                        if required_layer12 is not None:
                            if suffix:
                                required_layer12 = re.sub(r"\.md$", "_zh_cn.md", required_layer12)
                            fixed_direct_links.append(required_layer12)
                            if required_layer12 not in linked_paths(module_steps[checkpoint]):
                                fail(errors, path, f"{route}/{entry.get('source_step')}: {lang} {module}/{checkpoint} lacks exact direct owner link {required_layer12}")
                    if not refs and (not fixed_direct_links or not any(link in linked_paths(body) for link in fixed_direct_links for body in (module_steps[checkpoint] for checkpoint in checkpoints))):
                        fail(errors, path, f"{route}/{entry.get('source_step')}: owner_refs is empty and no fixed direct L1/L2 target is actually linked from the designated checkpoint set")
                    for owner in refs:
                        owner_path = root / "references/coding/layer-03-workflow-checkpoints" / f"{owner}{suffix}.md"
                        if not owner_path.is_file():
                            fail(errors, path, f"{route}/{entry.get('source_step')}: missing {lang} owner reference {owner}")
                            continue
                        expected_link = f"../../layer-03-workflow-checkpoints/{owner}{suffix}.md"
                        owner_checkpoints = [checkpoint for checkpoint in checkpoints
                                             if owner in MODULE_CHECKPOINT_L3_OWNERS.get(module, {}).get(checkpoint, set())]
                        if not owner_checkpoints or not any(expected_link in linked_paths(module_steps[checkpoint]) for checkpoint in owner_checkpoints):
                            fail(errors, path, f"{route}/{entry.get('source_step')}: {lang} owner {owner} is not linked from its designated numbered checkpoint")
                        if target.get("consumption") == "transitive":
                            required_owner_link = L3_REQUIRED_LAYER12_LINK.get(owner)
                            if required_owner_link is None:
                                fail(errors, path, f"{route}/{entry.get('source_step')}: no fixed Layer-01/02 target contract for transitive owner {owner}")
                            else:
                                required_owner_link = re.sub(r"\.md$", "_zh_cn.md", required_owner_link) if suffix else required_owner_link
                                owner_text = owner_path.read_text(encoding="utf-8")
                                operational = owner_text.split("\n## Related concepts", 1)[0].split("\n## 相关概念", 1)[0]
                                if required_owner_link not in linked_paths(operational):
                                    fail(errors, path, f"{route}/{entry.get('source_step')}: transitive {lang} owner {owner} lacks its fixed owner call {required_owner_link}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    errors = check_repository(args.root.resolve())
    if errors:
        print("Layer-04 workflow map validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("Layer-04 workflow map validation passed (seven-checkpoint routes and eight bilingual module maps).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
