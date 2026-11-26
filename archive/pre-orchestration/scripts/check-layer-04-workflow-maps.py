#!/usr/bin/env python3
"""校验 Coding 路线图、阶段清单和规则引用。"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from urllib.parse import unquote

from workflow_module_contracts import (
    HOOKS_DIR, MODULES, MODULE_CHECKPOINTS, MODULE_CHECKPOINT_L3_OWNERS,
    MODULE_CHECKPOINT_LAYER12_TARGETS, MODULE_HOOKS, ROUTE_MODULES, ROUTES_DIR,
    TOP_PREFIXES,
)

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


def parse_diagram(text: str, path: Path, header: str, errors: list[str]):
    section = get_section(text, header)
    if section is None:
        fail(errors, path, f"expected exactly one {header}")
        return set(), set()
    diagrams = FENCE.findall(section)
    if len(diagrams) != 1:
        fail(errors, path, "expected exactly one mermaid flowchart")
        return set(), set()
    raw = diagrams[0]
    declarations = NODE.findall(raw)
    nodes = set(declarations)
    if len(declarations) != len(nodes):
        fail(errors, path, "duplicate map node ID")
    edges = {(match.group(1), match.group(3)) for match in EDGE.finditer(raw)}
    for source, target in edges:
        if source not in nodes or target not in nodes:
            fail(errors, path, f"edge references undeclared node {source} -> {target}")
    return nodes, edges


def check_verification_navigation(text: str, path: Path, errors: list[str]) -> None:
    nodes, edges = parse_diagram(text, path, "## 验证与重验导航", errors)
    required = {
        ("D_RESULT", "VR06"), ("D_RESULT", "VR05"),
        ("D_RESULT", "VR_NEEDS"), ("D_RESULT", "VR_BLOCK"),
        ("VR_SCOPE", "VR_EXEC"), ("VR_EXEC", "VR_HANDOFF"), ("VR_HANDOFF", "VR01"),
    }
    for source, target in sorted(required - edges):
        fail(errors, path, f"required verification edge {source} -> {target} is missing")
    for source, target in sorted(edges - required - {("VR_HANDOFF", "VR_BLOCK")}):
        if target in {"VR06", "VR_EXEC", "VR_HANDOFF"} or source in {
            "VR_HANDOFF", "VR06", "VR_NEEDS", "VR_BLOCK",
        }:
            fail(errors, path, f"unexpected verification edge {source} -> {target}; possible gate bypass")
    reached = {"VR00"}
    while True:
        next_nodes = {target for source, target in edges if source in reached} - reached
        if not next_nodes:
            break
        reached.update(next_nodes)
    for node in sorted(nodes - reached):
        fail(errors, path, f"orphan/unreachable map node {node}")


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


def check_module(root: Path, module: str, lang: str, errors: list[str]) -> None:
    path = root / HOOKS_DIR / f"{MODULE_HOOKS[module]}.md"
    if not path.is_file():
        fail(errors, path, "missing module checklist")
        return
    text = path.read_text(encoding="utf-8")
    ids = module_checkpoint_ids(text, path, lang, errors)
    expected_ids = list(MODULE_CHECKPOINTS[module])
    if ids != expected_ids:
        fail(errors, path, f"module checklist must use the fixed ordered checkpoints {expected_ids}")
    step_section = get_section(text, LIST_HEADERS[lang]) or ""
    if ids and not re.search(r"complete|完成", step_section, re.I):
        fail(errors, path, "module checklist must define its completion result")
    if "../references/coding/layer-03-workflow-checkpoints/module-entry-resolution.md" not in linked_paths(step_section):
        fail(errors, path, "numbered entry step does not consume module-entry-resolution")
    layer3_owners = MODULE_CHECKPOINT_L3_OWNERS[module]
    layer12_targets = MODULE_CHECKPOINT_LAYER12_TARGETS.get(module, {})
    steps = list(STEP.finditer(step_section))
    for index, step in enumerate(steps):
        checkpoint = step.group(2)
        end = steps[index + 1].start() if index + 1 < len(steps) else len(step_section)
        links = linked_paths(step_section[step.start():end])
        targets = layer12_targets.get(checkpoint, ())
        if isinstance(targets, str):
            targets = (targets,)
        owners = layer3_owners.get(checkpoint, ())
        owner_links = (
            f"../references/coding/layer-03-workflow-checkpoints/{owner}.md"
            for owner in sorted(owners)
        )
        for target in (*targets, *owner_links):
            if target not in links:
                fail(errors, path, f"{checkpoint} must link to {target}")
    if module == "verification-repair":
        check_verification_navigation(text, path, errors)


def check_route(root: Path, route: str, lang: str, errors: list[str]):
    suffix = ""
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
        target = f"../hooks/{MODULE_HOOKS[expected_modules[i]]}.md"
        if target not in linked_paths(step_text):
            fail(errors, path, f"{expected_ids[i]} must bind its exact phase Hook {target}")
    nodes, edges = parse_diagram(text, path, MAP_HEADERS[lang], errors)
    if nodes != {*expected_ids, "DONE"}:
        fail(errors, path, "route map must contain only the ordered stages and completion")
    required_edges = set(zip(expected_ids, [*expected_ids[1:], "DONE"]))
    for edge in sorted(edges - required_edges):
        fail(errors, path, f"unexpected route edge {edge[0]} -> {edge[1]}; possible gate bypass")
    for edge in sorted(required_edges - edges):
        fail(errors, path, f"required route edge {edge[0]} -> {edge[1]} is missing")
    recovery = linked_paths(get_section(text, "## 前置补证与恢复") or "")
    for hook in ("recovery", "entry", "planning", "repair", "verification"):
        target = f"../hooks/{hook}.md"
        if target not in recovery:
            fail(errors, path, f"route recovery must link to {target}")


def check_repository(root: Path) -> list[str]:
    errors: list[str] = []
    for route in ROUTE_MODULES:
        check_route(root, route, "zh", errors)
    for module in MODULES:
        check_module(root, module, "zh", errors)
    workflow_path = root / WORKFLOW
    if workflow_path.is_file():
        ci = workflow_path.read_text(encoding="utf-8")
        for required in (SCRIPT, TEST, f"python3 {SCRIPT}", f"python3 -m unittest discover -s tests -p '{Path(TEST).name}'"):
            if required not in ci:
                fail(errors, workflow_path, f"missing trigger or command {required}")
    return errors


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
    print("Coding 路线图、跨阶段返回与 Hook 检查清单校验通过。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
