"""采集并比较基准源码、数据集和服务元数据的证据快照。"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .serialization import _canonical_hash, _json_safe, _sha256


def _source_manifest(case_module: Any, case_ids: Sequence[str], repo_root: Path) -> list[str]:
    paths = list(case_module._COMMON_SOURCES)
    case_sources = case_module._CASE_SOURCES
    for case_id in case_ids:
        paths.extend(case_sources[case_id])
    paths.extend(
        [
            ".agents/skills/token-io-decoupling-dev/tests/mcp/support/benchmark_cases.py",
            ".agents/skills/token-io-decoupling-dev/tests/mcp/support/benchmark_metrics.py",
            ".agents/skills/token-io-decoupling-dev/tests/mcp/support/optimization_benchmark.py",
        ]
    )
    # 旧入口已转为兼容层，当前合成报告还须绑定实际实现文件。
    paths.extend(
        f".agents/skills/token-io-decoupling-dev/tests/mcp/support/benchmark_support/{path.name}"
        for path in Path(__file__).resolve().parent.glob("*.py")
    )
    dataset_path = Path(case_module.DATASET_PATH).resolve(strict=True)
    paths.append(dataset_path.relative_to(repo_root.resolve()).as_posix())
    return sorted(set(str(path) for path in paths))


def _snapshot_sources(
    repo_root: Path, paths: Sequence[str]
) -> tuple[dict[str, str | None], dict[str, str]]:
    hashes: dict[str, str | None] = {}
    errors: dict[str, str] = {}
    for relative in paths:
        try:
            hashes[relative] = _sha256((repo_root / relative).read_bytes())
        except OSError as exc:
            hashes[relative] = None
            errors[relative] = type(exc).__name__
    return hashes, errors


def _dataset_snapshot(case_module: Any, case_ids: Sequence[str]) -> dict[str, object]:
    path = Path(case_module.DATASET_PATH)
    try:
        raw = path.read_bytes()
        dataset = json.loads(raw)
        discovered = tuple(item["case_id"] for item in dataset["cases"])
        return {
            "sha256": _sha256(raw),
            "case_ids": list(discovered),
            "matches_fixed_case_order": discovered == tuple(case_ids),
            "error_type": None,
        }
    except Exception as exc:
        return {
            "sha256": None,
            "case_ids": None,
            "matches_fixed_case_order": False,
            "error_type": type(exc).__name__,
        }


def _metadata_snapshot(
    case_module: Any, case_ids: Sequence[str]
) -> tuple[dict[str, str | None], dict[str, str]]:
    hashes: dict[str, str | None] = {}
    errors: dict[str, str] = {}
    for case_id in case_ids:
        try:
            service = case_module._CASES[case_id]["service"]
            metadata, _source_paths = case_module._service_metadata(service)
            hashes[case_id] = _canonical_hash(metadata)
        except Exception as exc:
            hashes[case_id] = None
            errors[case_id] = type(exc).__name__
    return hashes, errors


def _dataset_protocol_version(case_module: Any) -> object:
    dataset = getattr(case_module, "DATASET", None)
    if isinstance(dataset, Mapping):
        return _json_safe(dataset.get("protocol_version"))
    return _json_safe(getattr(dataset, "protocol_version", None))


@dataclass(frozen=True)
class ContentSnapshot:
    hashes: dict[str, str | None]
    errors: dict[str, str]

    def initial(self) -> dict[str, object]:
        return {"before": self.hashes, "after": None, "stable": None, "errors_before": self.errors}


@dataclass(frozen=True)
class EvidenceSnapshot:
    sources: ContentSnapshot
    dataset: dict[str, object]
    metadata: ContentSnapshot

    @classmethod
    def capture(cls, case_module: Any, case_ids: Sequence[str], root: Path) -> EvidenceSnapshot:
        source_paths = _source_manifest(case_module, case_ids, root)
        return cls(
            ContentSnapshot(*_snapshot_sources(root, source_paths)),
            _dataset_snapshot(case_module, case_ids),
            ContentSnapshot(*_metadata_snapshot(case_module, case_ids)),
        )

    def initial(self) -> dict[str, object]:
        return {
            "sources": self.sources.initial(),
            "dataset": {"before": self.dataset, "after": None, "stable": None},
            "metadata": self.metadata.initial(),
        }

    def blocking_reason(self) -> str | None:
        if self.sources.errors or self.metadata.errors:
            return "source_or_metadata_snapshot_failed"
        if (
            self.dataset.get("error_type") is not None
            or self.dataset.get("matches_fixed_case_order") is not True
        ):
            return "dataset_does_not_match_fixed_case_order"
        return None

    def compare(self, case_module: Any, case_ids: Sequence[str], root: Path) -> dict[str, object]:
        return _fingerprints(
            case_module,
            case_ids,
            root,
            list(self.sources.hashes),
            self.sources.errors,
            self.sources.hashes,
            self.dataset,
            self.metadata.hashes,
            self.metadata.errors,
        )


def _fingerprints(
    case_module: Any,
    case_ids: Sequence[str],
    repo_root: Path,
    source_paths: Sequence[str],
    source_errors_before: Mapping[str, str],
    source_before: Mapping[str, str | None],
    dataset_before: Mapping[str, object],
    metadata_before: Mapping[str, str | None],
    metadata_errors_before: Mapping[str, str],
) -> dict[str, object]:
    source_after, source_errors_after = _snapshot_sources(repo_root, source_paths)
    dataset_after = _dataset_snapshot(case_module, case_ids)
    metadata_after, metadata_errors_after = _metadata_snapshot(case_module, case_ids)
    return {
        "sources": {
            "before": dict(source_before),
            "after": source_after,
            "errors_before": dict(source_errors_before),
            "errors_after": source_errors_after,
            "stable": not source_errors_before
            and not source_errors_after
            and dict(source_before) == source_after,
        },
        "dataset": {
            "before": dict(dataset_before),
            "after": dataset_after,
            "stable": (
                dataset_before.get("error_type") is None
                and dataset_after.get("error_type") is None
                and dataset_before.get("sha256") == dataset_after.get("sha256")
                and dataset_before.get("matches_fixed_case_order") is True
                and dataset_after.get("matches_fixed_case_order") is True
            ),
        },
        "metadata": {
            "before": dict(metadata_before),
            "after": metadata_after,
            "errors_before": dict(metadata_errors_before),
            "errors_after": metadata_errors_after,
            "stable": not metadata_errors_before
            and not metadata_errors_after
            and dict(metadata_before) == metadata_after,
        },
    }
