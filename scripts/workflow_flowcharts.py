"""校验工作流流程图及其对 Hook 合同的覆盖。"""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Iterable

from workflow_checkpoint_lookup import find_block, walk_blocks


MERMAID = re.compile(r"^```mermaid\nflowchart (?:TD|TB|LR|RL|BT)\n(.*?)^```$", re.M | re.S)
NODE_ID = r"[A-Z][A-Z0-9_]*"
NODE = re.compile(rf"({NODE_ID})(?:\[[^\n]+\]|\{{[^\n]+\}}|\(\[[^\n]+\]\))")
EDGE = re.compile(
    rf"({NODE_ID})\s+(-->(?:\|[^|]+\|)?|-\.->|-\. .+? \.->)\s+({NODE_ID})"
)


def reachable_nodes(root: str, edges: Iterable[tuple[str, str]]) -> set[str]:
    neighbors: dict[str, set[str]] = defaultdict(set)
    for start, end in edges:
        neighbors[start].add(end)
    pending = {root}
    reached = set()
    while pending:
        node = pending.pop()
        reached.add(node)
        pending.update(neighbors[node] - reached)
    return reached


def parse_flowchart(location: str, text: str) -> tuple[list[str], list[tuple[str, str, bool]]]:
    diagrams = MERMAID.findall(text)
    if len(diagrams) != 1:
        raise ValueError(f"{location} 须包含一个 Mermaid 流程图")
    nodes = []
    edges = []
    lines = [line.strip() for line in diagrams[0].splitlines()]
    for line in lines:
        if not line:
            continue
        if node := NODE.fullmatch(line):
            nodes.append(node[1])
        elif edge := EDGE.fullmatch(line):
            edges.append((edge[1], edge[3], edge[2].startswith("-.")))
        else:
            raise ValueError(f"{location} 无效的流程图节点或连线：{line}")
    if len(set(nodes)) != len(nodes):
        raise ValueError(f"{location} 存在重复流程图节点")
    if 'START(["开始"])' not in lines or 'END(["结束"])' not in lines:
        raise ValueError(f"{location} 须声明「开始」和「结束」节点")
    known_nodes = set(nodes)
    if unknown := {node for start, end, _ in edges for node in (start, end)} - known_nodes:
        raise ValueError(f"{location} 存在未声明的节点：{'、'.join(sorted(unknown))}")
    if any(end == "START" or start == "END" for start, end, _ in edges):
        raise ValueError(f"{location} 「开始」只能引出连线，「结束」只能接收连线")
    if missing := known_nodes - reachable_nodes("START", ((start, end) for start, end, _ in edges)):
        raise ValueError(f"{location} 从「开始」无法到达：{'、'.join(sorted(missing))}")
    if missing := known_nodes - reachable_nodes("END", ((end, start) for start, end, _ in edges)):
        raise ValueError(f"{location} 无法汇入「结束」：{'、'.join(sorted(missing))}")
    return nodes, edges


def validate_hook_flowcharts(flowcharts: dict, documents: Iterable[dict]) -> None:
    if flowcharts["kind"] != "section":
        raise ValueError("hook-flowcharts 须为章节")
    contracts = {
        f"{document['id']}-flowchart": document for document in documents
        if document.get("document_type") == "hook-contract"
    }
    charts = dict(pair for entry in flowcharts["blocks"] for pair in entry.items())
    if contracts.keys() != charts.keys():
        raise ValueError(f"Hook 子流程图与合同不匹配：{'、'.join(sorted(contracts.keys() ^ charts.keys()))}")
    for name, contract in contracts.items():
        chart = charts[name]
        if chart["kind"] != "section":
            raise ValueError(f"{name} 须为 Hook 子流程图章节")
        text = "\n".join(block["text"] for _, block, _ in walk_blocks(chart["blocks"]) if block["kind"] == "markdown")
        nodes, _ = parse_flowchart(name, text)
        expected = {
            block_id.upper().replace("-", "_") for entry in contract["blocks"]
            for block_id, block in entry.items() if block["kind"] == "section"
        }
        _, execution, _ = find_block(contract, "execution")
        for _, block, _ in walk_blocks(execution["blocks"]):
            if block["kind"] == "markdown":
                expected.update(f"EXECUTION_{item}" for item in re.findall(r"(?m)^(\d+)\. ", block["text"]))
        if missing := expected - set(nodes):
            raise ValueError(f"{name} 缺少 Hook 子项流程节点：{'、'.join(sorted(missing))}")


def route_blocks(document: dict, flowcharts: dict) -> list[dict]:
    if document.get("document_type") != "workflow-route":
        return document["blocks"]
    _, overview, _ = find_block(document, "flowchart")
    blocks = [*overview["blocks"][:-1], {"hook-flowcharts": flowcharts}]
    return [
        {"flowchart": {**overview, "blocks": blocks}} if "flowchart" in entry else entry
        for entry in document["blocks"]
    ]
