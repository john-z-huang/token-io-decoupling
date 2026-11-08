"""文档路径语言、镜像路径及层级导航权限。"""

from __future__ import annotations

from pathlib import PurePosixPath

from .constants import _LANGUAGE_SWITCH_LABELS, _MODULES, _PAIR_ROOT_SET, _ROUTE_MODULES, ZH_SUFFIX


def _coding_reference_layer(parts: tuple[str, ...]) -> str | None:
    if parts[:3] == ("references", "coding", "layer-01-fundamental-concepts"):
        return "layer-01"
    if parts[:3] == ("references", "coding", "layer-02-workflow-concepts"):
        return "layer-02"
    if parts[:3] == ("references", "coding", "layer-03-workflow-checkpoints"):
        return "layer-03"
    if parts[:3] == ("references", "coding", "layer-04-workflows"):
        return "layer-04-module" if len(parts) > 3 and parts[3] == "modules" else "layer-04-route"
    return None


def path_layer(path: PurePosixPath) -> str:
    parts = path.parts
    if parts[:3] == ("instruction-compiler", "sources", "skill"):
        parts = parts[3:]
    layer = _coding_reference_layer(parts)
    if layer is not None:
        return layer
    if parts[:2] == ("references", "share"):
        return "shared-protocols"
    if parts and parts[0] == "references":
        return "references"
    if parts[:2] == ("workflows", "checkpoint"):
        return "checkpoint"
    if parts[:2] == ("workflows", "exist-workflow"):
        return "exist-workflow"
    if str(path) in {
        "instruction-compiler/sources/skill/workflows/coding.md",
        "instruction-compiler/sources/skill/workflows/coding_zh_cn.md",
    }:
        return "coding-selector"
    return "entry"


def path_language(path: PurePosixPath) -> str:
    return "zh" if path.parts[:2] == ("docs", "zh-cn") or path.name.endswith(ZH_SUFFIX) else "en"


def is_language_switch(label: str) -> bool:
    return label.strip().casefold() in _LANGUAGE_SWITCH_LABELS


def is_navigation_document(path: PurePosixPath) -> bool:
    return path.name in {"README.md", "README_zh_cn.md", "INDEX.md", "INDEX_zh_cn.md"}


def counterpart(path: PurePosixPath) -> PurePosixPath:
    if path.parts[:2] == ("docs", "zh-cn"):
        return PurePosixPath("docs", path.name)
    if path == PurePosixPath("docs/index.md"):
        return PurePosixPath("docs/zh-cn/index.md")
    if path.name.endswith(ZH_SUFFIX):
        return path.with_name(path.name.removesuffix(ZH_SUFFIX) + ".md")
    return path.with_name(path.stem + ZH_SUFFIX)


def _allowed_route_link(
    target: str,
    is_navigation: bool,
    source_path: PurePosixPath | None,
    target_path: PurePosixPath | None,
) -> bool:
    same_layer_navigation = is_navigation and target == "layer-04-route"
    module_root = PurePosixPath(
        "instruction-compiler/sources/skill/references/coding/layer-04-workflows/modules"
    )
    canonical_modules = {
        module_root / f"{module}{suffix}.md" for module in _MODULES for suffix in ("", "_zh_cn")
    }
    if is_navigation and target == "layer-04-module" and target_path is not None:
        return target_path.parent == module_root and target_path in canonical_modules
    if same_layer_navigation or target in {
        "shared-protocols",
        "layer-01",
        "layer-02",
        "layer-03",
    }:
        return True
    if target != "layer-04-module" or source_path is None or target_path is None:
        return False
    route_root = PurePosixPath(
        "instruction-compiler/sources/skill/references/coding/layer-04-workflows"
    )
    route_name = source_path.stem.removesuffix("_zh_cn")
    canonical_route = route_root / f"{route_name}.md"
    if source_path not in {canonical_route, route_root / f"{route_name}_zh_cn.md"}:
        return False
    if target_path.parent != module_root or target_path not in canonical_modules:
        return False
    return target_path.stem.removesuffix("_zh_cn") in _ROUTE_MODULES.get(route_name, ())


def allowed_link(
    source: str,
    target: str,
    is_navigation: bool,
    source_path: PurePosixPath | None = None,
    target_path: PurePosixPath | None = None,
) -> bool:
    same_layer_navigation = is_navigation and source == target
    if source in {"references", "layer-01"}:
        return same_layer_navigation or target == "layer-01"
    if source in {"checkpoint", "layer-02"}:
        return same_layer_navigation or target in {"references", "layer-01"}
    if source in {"exist-workflow", "layer-03"}:
        return same_layer_navigation or target in {"shared-protocols", "layer-01", "layer-02"}
    if source == "layer-04-route":
        return _allowed_route_link(target, is_navigation, source_path, target_path)
    if source in {"layer-04-module", "layer-04"}:
        return same_layer_navigation or target in {
            "shared-protocols",
            "layer-01",
            "layer-02",
            "layer-03",
        }
    if source == "coding-selector":
        return is_navigation or target in {
            "exist-workflow",
            "layer-01",
            "layer-02",
            "layer-03",
            "layer-04",
            "layer-04-route",
            "layer-04-module",
        }
    return True


def is_bilingual_document(path: str) -> bool:
    return (
        path in _PAIR_ROOT_SET
        or mirror_path(path) in _PAIR_ROOT_SET
        or path.startswith("instruction-compiler/sources/skill/references/")
        or path.startswith(".agents/skills/token-io-decoupling-dev/references/")
    )


def mirror_path(path: str) -> str:
    pure = PurePosixPath(path)
    if pure.parts[:2] == ("docs", "zh-cn"):
        return PurePosixPath("docs", pure.name).as_posix()
    if path == "docs/index.md":
        return "docs/zh-cn/index.md"
    if pure.name.endswith(ZH_SUFFIX):
        return pure.with_name(pure.name.removesuffix(ZH_SUFFIX) + ".md").as_posix()
    return pure.with_name(pure.stem + ZH_SUFFIX).as_posix()
