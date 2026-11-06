"""作者输入、单次编译追溯和静态交付产物的固定数据契约。"""

from typing import Literal, NotRequired, TypedDict


class Instruction(TypedDict):
    """完整内联正文及其指纹和来源身份，供节点、workflow 与政策复用。"""

    text: str
    content_sha256: str
    instruction_ids: list[str]


class FragmentInstruction(TypedDict):
    """片段正文沿用外部协议的 text_sha256，不与文件字节 Hash 混用。"""

    text: str
    text_sha256: str
    instruction_ids: list[str]


class HookContract(TypedDict):
    """从事件规范文档解析的机器结构；语义判断仍以同一文档正文为准。"""

    schema_version: Literal[1]
    event_id: str
    modes: list[str]
    required_facts: list[str]
    required_evidence: list[str]
    allowed_outcomes: list[str]


class EventInstruction(HookContract, Instruction):
    """同一规范文档的结构字段与共享约束加当前事件正文。"""


class PolicyInstruction(Instruction):
    """细粒度建议工具所需的政策正文、具名区段和选项描述。"""

    sections: dict[str, str]
    choices: dict[str, dict[str, str]]


class NodeRequirements(TypedDict):
    """静态查询要求；保留的 next_checkpoint_ids 字段不用于模拟流程推进。"""

    node_id: str
    required_facts: list[str]
    required_evidence: list[str]
    legal_branches: list[str]
    evaluation_mode: str
    failure_action: str
    next_checkpoint_ids: list[str]


class RuleNode(NodeRequirements):
    """节点要求与唯一 owner 地址；作者阶段为文件，产品阶段为 compiled 引用。"""

    owner_path: str
    owner_section: str


class RuleRegistry(TypedDict):
    """已审核节点的固定注册表，作者输入和产品输出均使用 contract 3。"""

    contract_version: int
    nodes: list[RuleNode]


class IndexNode(TypedDict):
    """把查询 ID 映射到默认指令片段，不保存当前任务处于哪个步骤。"""

    node_id: str
    default_fragment_ids: list[str]


class AuthorFragment(TypedDict):
    """作者树内的显式选段及依赖；section 缺省表示选择完整文档。"""

    fragment_id: str
    node_id: str
    source_path: str
    section: NotRequired[str]
    dependencies: NotRequired[list[str]]


class CompiledFragment(TypedDict):
    """产品片段的静态描述；作者文件路径在发布前移除。"""

    fragment_id: str
    node_id: str
    section: str
    dependencies: NotRequired[list[str]]


class AuthorContextIndex(TypedDict):
    """供编译器验证与展开静态指令的作者索引，使用 schema 2。"""

    schema_version: int
    nodes: list[IndexNode]
    fragments: list[AuthorFragment]


class CompiledContextIndex(TypedDict):
    """保持查询接口所需的片段关系，不提供运行时作者文件回退读取。"""

    schema_version: int
    nodes: list[IndexNode]
    fragments: list[CompiledFragment]


class CheckpointListing(NodeRequirements):
    """纯文档查询要求与一个当前中文文档地址，供无 MCP 场景检索。"""

    document: str


class DocumentIndex(TypedDict):
    """Skill 内的单中文导航索引；schema 3 与外部查询信封版本分别维护。"""

    schema_version: int
    language: Literal["zh_cn"]
    events: dict[str, str]
    workflows: dict[str, str]
    checkpoints: dict[str, CheckpointListing]
    fragments: dict[str, list[str]]


class ClosureTrace(TypedDict):
    """一次显式指令组合的来源与规模，navigation_expanded 固定为 False。"""

    sources: list[str]
    characters: int
    bytes: int
    navigation_expanded: Literal[False]


class SourceTrace(TypedDict):
    """单次编译的选段追溯和源 Hash，不是 Agent 的工作流状态存储。"""

    closures: dict[str, ClosureTrace]
    source_hashes: dict[str, str]


class TextSize(TypedDict):
    """分别记录 Unicode 字符数和 UTF-8 字节数，避免预算口径混淆。"""

    characters: int
    bytes: int


class DeliveryReport(TypedDict, total=False):
    """编译完成后填入的实际交付规模，允许尚未交付时字段为空缺。"""

    default_contract: TextSize
    skill_entry: TextSize
    navigation_expanded: Literal[False]


class CompilationReport(SourceTrace):
    """开发验收所用静态来源与交付报告，不进入任务运行状态。"""

    delivery: DeliveryReport


class CompiledContent(TypedDict):
    """参与构建身份计算的稳定内容，不包含由它推导出的真实构建 ID。"""

    schema_version: int
    compiler_version: str
    language: Literal["zh_cn"]
    registry: RuleRegistry
    context_index: CompiledContextIndex
    nodes: dict[str, Instruction]
    fragments: dict[str, FragmentInstruction]
    policies: dict[str, PolicyInstruction]
    events: dict[str, EventInstruction]
    workflows: dict[str, Instruction]
    document_units: dict[str, str]


class CompiledDocument(CompiledContent):
    """最终运行时资源；绑定构建 ID 与 Skill 完整文件清单。"""

    build_id: str
    skill_files: dict[str, str]


class CompilationSummary(TypedDict):
    """开发 CLI 的结果摘要；正文规模用于审查，不声明成本或性能收益。"""

    build_id: str
    generated_files: int
    resource_bytes: int
    instruction_characters: dict[str, int]
    event_characters: dict[str, int]
