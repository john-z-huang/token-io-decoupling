#!/usr/bin/env python3
"""Check Layer-03 Mermaid route maps against checklists, mirrors, AGENTS rules, and CI.

This is a structural check, not a proof of semantic equivalence of translations.
Nodes have stable language-independent IDs; matching IDs and edges ensure that
translations cannot silently change executable route topology.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROUTES = Path('references/coding/layer-03-workflows')
WORKFLOW = Path('.github/workflows/multilingual-docs.yml')
SCRIPT = 'scripts/check-layer-03-workflow-maps.py'
TEST = 'tests/test_check_layer_03_workflow_maps.py'
RULE_TITLE = {'en': '## Layer-03 workflow maps', 'zh': '## Layer-03 工作流路线图'}
MAP_TITLE = {'en': '## Workflow map', 'zh': '## 工作流路线图'}
CHECKLIST_TITLE = {'en': '## Ordered route checklist', 'zh': '## 路线顺序检查清单'}
FENCE_RE = re.compile(r'^\x60{3}([^\n]*)\n(.*?)^\x60{3}\s*$', re.M | re.S)
STEP_RE = re.compile(r'(?m)^(\d+)\.\s+\*\*')
NODE_RE = re.compile(r'^\s*([A-Z][A-Z0-9_]*)\s*[\[\{(]')
ID_RE = re.compile(r'[A-Z][A-Z0-9_]*')

ROUTE_SPECS = {
    'single-agent': {
        'prefix': 'S',
        'steps': ('Contract', 'Environment', 'Mode', 'Session', 'Context', 'Decision',
                  'Implementation', 'Stage Feedback', 'Control', 'Verification',
                  'Repair', 'Documentation', 'Git', 'Acceptance'),
        'branches': {'D_RECON', 'ACT_RECON', 'D_CONTROL', 'D_VERIFY', 'D_DOC', 'D_GIT', 'BLOCK', 'DONE'},
        'edges': {
            ('S01', 'S02'), ('S02', 'S03'), ('S03', 'S04'), ('S04', 'S05'),
            ('S05', 'D_RECON'), ('D_RECON', 'ACT_RECON'), ('ACT_RECON', 'S05'), ('D_RECON', 'S06'),
            ('S06', 'S07'), ('S07', 'S08'), ('S08', 'S09'), ('S09', 'D_CONTROL'),
            ('D_CONTROL', 'S05'), ('D_CONTROL', 'S06'), ('D_CONTROL', 'S10'), ('D_CONTROL', 'BLOCK'),
            ('S10', 'D_VERIFY'), ('D_VERIFY', 'S11'), ('D_VERIFY', 'S12'), ('D_VERIFY', 'BLOCK'),
            ('S11', 'S10'), ('S12', 'D_DOC'), ('D_DOC', 'S10'), ('D_DOC', 'S06'),
            ('D_DOC', 'S13'), ('S13', 'D_GIT'), ('D_GIT', 'S14'), ('D_GIT', 'BLOCK'),
            ('S14', 'DONE'),
        },
        'forbidden': re.compile(r'\b(?:Child Creation|Child Dispatch|Worker Memo|Context Bootstrap|'
                                r'Child Lifecycle|Child Role Allocation)\b|子代理创建|子代理派发|'
                                r'子代理生命周期|子代理职责分配|跨 Worker', re.I),
    },
    'multi-agent': {
        'prefix': 'M',
        'steps': ('Contract', 'Environment', 'Mode', 'Session', 'Allocation', 'Context',
                  'Decision', 'Slice', 'Child Creation', 'Dispatch', 'Implementation',
                  'Verification', 'Repair', 'Documentation', 'Git', 'Acceptance'),
        'branches': {'D_BOOT', 'ACT_BOOT_PLAN', 'D_RECON', 'ACT_RECON_PLAN',
                     'D_MEMO', 'ACT_MEMO', 'D_CONTROL', 'D_VERIFY', 'D_DOC', 'D_GIT', 'BLOCK', 'DONE'},
        'edges': {
            ('M01', 'M02'), ('M02', 'M03'), ('M03', 'M04'), ('M04', 'M05'),
            ('M05', 'D_BOOT'), ('D_BOOT', 'ACT_BOOT_PLAN'), ('ACT_BOOT_PLAN', 'M06'), ('D_BOOT', 'M06'),
            ('M06', 'M07'), ('M07', 'D_RECON'), ('D_RECON', 'ACT_RECON_PLAN'),
            ('ACT_RECON_PLAN', 'M08'), ('D_RECON', 'M08'),
            ('M08', 'M09'), ('M09', 'D_MEMO'), ('M10', 'M11'),
            ('D_MEMO', 'ACT_MEMO'), ('ACT_MEMO', 'M10'), ('D_MEMO', 'M10'),
            ('M11', 'D_CONTROL'), ('D_CONTROL', 'M06'), ('D_CONTROL', 'M07'),
            ('D_CONTROL', 'M12'), ('D_CONTROL', 'BLOCK'), ('M12', 'D_VERIFY'),
            ('D_VERIFY', 'M13'), ('D_VERIFY', 'M14'), ('D_VERIFY', 'BLOCK'),
            ('M13', 'M12'), ('M14', 'D_DOC'), ('D_DOC', 'M12'), ('D_DOC', 'M07'),
            ('D_DOC', 'M15'), ('M15', 'D_GIT'), ('D_GIT', 'M16'), ('D_GIT', 'BLOCK'),
            ('M16', 'DONE'),
        },
    },
}


def section(content: str, header: str) -> tuple[str, int] | None:
    """Locate exactly one top-level section, returning body and heading offset."""
    hits = list(re.finditer(r'(?m)^' + re.escape(header) + r'\s*$', content))
    if len(hits) != 1:
        return None
    match = hits[0]
    following = re.search(r'(?m)^## ', content[match.end():])
    end = match.end() + following.start() if following else len(content)
    return content[match.end():end], match.start()


def parse_map(raw: str, path: Path, errors: list[str]) -> tuple[dict[str, str], set[tuple[str, str]]]:
    lines = raw.splitlines()
    if not lines or not re.match(r'^flowchart\s+(?:TD|TB|LR)\s*$', lines[0].strip()):
        errors.append(f'{path}: Mermaid map must begin with flowchart TD/TB/LR')
    nodes: dict[str, str] = {}
    edges: set[tuple[str, str]] = set()
    for number, line in enumerate(lines, 1):
        match = NODE_RE.match(line)
        if match:
            name = match.group(1)
            if name in nodes:
                errors.append(f'{path}: duplicate Mermaid node {name} on map line {number}')
            nodes[name] = line
        if '-->' in line:
            left, right = line.split('-->', 1)
            src_match = ID_RE.match(left.strip())
            dst_match = ID_RE.match(right.strip())
            if src_match and dst_match:
                edges.add((src_match.group(), dst_match.group()))
            else:
                errors.append(f'{path}: unparsable Mermaid edge on map line {number}')
    for source, target in edges:
        if source not in nodes or target not in nodes:
            errors.append(f'{path}: edge {source} -> {target} refers to undefined node')
    return nodes, edges


def validate_route(root: Path, route: str, lang: str, errors: list[str]) -> tuple[set[str], set[tuple[str, str]]] | None:
    filename = f'coding-{route}{"_zh_cn" if lang == "zh" else ""}.md'
    path = root / ROUTES / filename
    if not path.is_file():
        errors.append(f'missing route file: {path}')
        return None
    content = path.read_text(encoding='utf-8')
    expected_header = MAP_TITLE[lang]
    map_section = section(content, expected_header)
    checklist_section = section(content, CHECKLIST_TITLE[lang])
    if map_section is None:
        errors.append(f'{path}: exactly one {expected_header} section is required')
        return None
    if checklist_section is None:
        errors.append(f'{path}: exactly one {CHECKLIST_TITLE[lang]} section is required')
        return None
    if map_section[1] >= checklist_section[1]:
        errors.append(f'{path}: workflow map must precede the ordered checklist')
    fences = list(FENCE_RE.finditer(content))
    maps = [f for f in fences if f.group(1).strip() == 'mermaid']
    if len(maps) != 1 or not (map_section[1] < maps[0].start() < checklist_section[1]):
        errors.append(f'{path}: exactly one mermaid code block must be inside the workflow map section')
        return None
    nodes, edges = parse_map(maps[0].group(2).strip(), path, errors)
    spec = ROUTE_SPECS[route]
    prefix = spec['prefix']
    steps = spec['steps']
    expected = {f'{prefix}{n:02d}' for n in range(1, len(steps) + 1)} | spec['branches']
    for name in sorted(expected - nodes.keys()):
        errors.append(f'{path}: missing required map node {name}')
    for name in sorted(nodes.keys() - expected):
        errors.append(f'{path}: unexpected map node {name}')
    for number, keyword in enumerate(steps, 1):
        node = f'{prefix}{number:02d}'
        if node in nodes and not re.search(r'\b' + re.escape(keyword) + r'\b', nodes[node], re.I):
            errors.append(f'{path}: node {node} must identify {keyword} checkpoint')
    recorded_steps = [int(match.group(1)) for match in STEP_RE.finditer(checklist_section[0])]
    wanted_steps = list(range(1, len(steps) + 1))
    if recorded_steps != wanted_steps:
        errors.append(f'{path}: checklist numbering must be {wanted_steps}, got {recorded_steps}')
    for edge in sorted(spec['edges'] - edges):
        errors.append(f'{path}: required map edge {edge[0]} -> {edge[1]} is missing')
    for edge in sorted(edges - spec['edges']):
        errors.append(f'{path}: unexpected map edge {edge[0]} -> {edge[1]}; update the approved route contract explicitly')
    skip_edges = (
        (('D_RECON', 'S06'), ('D_DOC', 'S13'), ('D_GIT', 'S14'))
        if route == 'single-agent' else
        (('D_BOOT', 'M06'), ('D_RECON', 'M08'), ('D_MEMO', 'M10'),
         ('D_DOC', 'M15'), ('D_GIT', 'M16'))
    )
    skip_words = (r'\b(?:no|N/A|disabled|not applicable)\b'
                  if lang == 'en' else r'不适用|不需要|关闭|无变化')
    for source, target in skip_edges:
        match = re.search(
            r'(?m)^\s*' + source + r'\s+--\s+(.+?)\s+-->\s+' + target + r'\s*
    # Extra edges are allowed only when they cannot bypass the permission/verification gates.
    forbidden_shortcuts = {
        (f'{prefix}03', f'{prefix}09'),
        (f'{prefix}07', f'{prefix}12' if route == 'multi-agent' else f'{prefix}10'),
        (f'{prefix}11' if route == 'multi-agent' else f'{prefix}09', 'DONE'),
        ('BLOCK', 'DONE'),
    }
    for edge in sorted(forbidden_shortcuts & edges):
        errors.append(f'{path}: unauthorized shortcut {edge[0]} -> {edge[1]}')
    if route == 'single-agent' and (bad := spec['forbidden'].search(maps[0].group(2))):
        errors.append(f'{path}: Single-Agent map contains an inapplicable child branch: {bad.group()}')
    for target in ('BLOCK', 'DONE'):
        if any(source == target for source, _ in edges):
            errors.append(f'{path}: terminal node {target} must have no outgoing edges')
    return set(nodes), edges


def check_repository(root: Path) -> list[str]:
    errors: list[str] = []
    for lang, policy_name in (('en', 'AGENTS.md'), ('zh', 'AGENTS_zh_cn.md')):
        path = root / policy_name
        if not path.is_file():
            errors.append(f'missing policy file: {path}')
            continue
        policy = path.read_text(encoding='utf-8')
        if RULE_TITLE[lang] not in policy:
            errors.append(f'{path}: missing workflow-map ownership section {RULE_TITLE[lang]}')
        if SCRIPT not in policy:
            errors.append(f'{path}: required validator command is not documented')
    for route in ROUTE_SPECS:
        english = validate_route(root, route, 'en', errors)
        chinese = validate_route(root, route, 'zh', errors)
        if english and chinese and english != chinese:
            errors.append(f'{route}: English and Chinese Mermaid node IDs/edges differ')
    path = root / WORKFLOW
    if not path.is_file():
        errors.append(f'missing workflow file: {path}')
    else:
        ci = path.read_text(encoding='utf-8')
        for required in (SCRIPT, TEST, f'python3 {SCRIPT}',
                         f"python3 -m unittest discover -s tests -p 'test_check_layer_03_workflow_maps.py'"):
            if required not in ci:
                errors.append(f'{path}: missing CI trigger or command: {required}')
        if '"**/*.md"' not in ci and "'**/*.md'" not in ci:
            errors.append(f'{path}: Markdown changes must trigger CI')
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    errors = check_repository(args.root.resolve())
    if errors:
        print('Layer-03 workflow map validation failed:', file=sys.stderr)
        for error in errors:
            print(f'- {error}', file=sys.stderr)
        return 1
    print('Layer-03 workflow map validation passed (2 routes x 2 languages; map/checklist/CI aligned).')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
,
            maps[0].group(2),
        )
        if not match or not re.search(skip_words, match.group(1), re.I):
            errors.append(f'{path}: conditional {source} -> {target} must label its skip/Not applicable path')
    # Extra edges are allowed only when they cannot bypass the permission/verification gates.
    forbidden_shortcuts = {
        (f'{prefix}03', f'{prefix}09'),
        (f'{prefix}07', f'{prefix}12' if route == 'multi-agent' else f'{prefix}10'),
        (f'{prefix}11' if route == 'multi-agent' else f'{prefix}09', 'DONE'),
        ('BLOCK', 'DONE'),
    }
    for edge in sorted(forbidden_shortcuts & edges):
        errors.append(f'{path}: unauthorized shortcut {edge[0]} -> {edge[1]}')
    if route == 'single-agent' and (bad := spec['forbidden'].search(maps[0].group(2))):
        errors.append(f'{path}: Single-Agent map contains an inapplicable child branch: {bad.group()}')
    for target in ('BLOCK', 'DONE'):
        if any(source == target for source, _ in edges):
            errors.append(f'{path}: terminal node {target} must have no outgoing edges')
    return set(nodes), edges


def check_repository(root: Path) -> list[str]:
    errors: list[str] = []
    for lang, policy_name in (('en', 'AGENTS.md'), ('zh', 'AGENTS_zh_cn.md')):
        path = root / policy_name
        if not path.is_file():
            errors.append(f'missing policy file: {path}')
            continue
        policy = path.read_text(encoding='utf-8')
        if RULE_TITLE[lang] not in policy:
            errors.append(f'{path}: missing workflow-map ownership section {RULE_TITLE[lang]}')
        if SCRIPT not in policy:
            errors.append(f'{path}: required validator command is not documented')
    for route in ROUTE_SPECS:
        english = validate_route(root, route, 'en', errors)
        chinese = validate_route(root, route, 'zh', errors)
        if english and chinese and english != chinese:
            errors.append(f'{route}: English and Chinese Mermaid node IDs/edges differ')
    path = root / WORKFLOW
    if not path.is_file():
        errors.append(f'missing workflow file: {path}')
    else:
        ci = path.read_text(encoding='utf-8')
        for required in (SCRIPT, TEST, f'python3 {SCRIPT}',
                         f"python3 -m unittest discover -s tests -p 'test_check_layer_03_workflow_maps.py'"):
            if required not in ci:
                errors.append(f'{path}: missing CI trigger or command: {required}')
        if '"**/*.md"' not in ci and "'**/*.md'" not in ci:
            errors.append(f'{path}: Markdown changes must trigger CI')
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    errors = check_repository(args.root.resolve())
    if errors:
        print('Layer-03 workflow map validation failed:', file=sys.stderr)
        for error in errors:
            print(f'- {error}', file=sys.stderr)
        return 1
    print('Layer-03 workflow map validation passed (2 routes x 2 languages; map/checklist/CI aligned).')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
