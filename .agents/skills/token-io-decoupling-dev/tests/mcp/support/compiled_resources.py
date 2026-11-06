"""Stage production-format JSON resources for isolated runtime contract tests."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from token_io_decoupling_core import rules


class CompiledResources:
    def __init__(self, root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        installed = rules.resources.files("token_io_decoupling_core").joinpath("_resources")
        self.document: dict[str, Any] = json.loads(
            installed.joinpath("instructions.json").read_bytes()
        )
        self.manifest: dict[str, Any] = json.loads(installed.joinpath("manifest.json").read_bytes())
        self.root = root / "package"
        self.resources = self.root / "_resources"
        self.resources.mkdir(parents=True)
        self.save()
        monkeypatch.setattr(rules.resources, "files", lambda _package: self.root)

    def save(self) -> None:
        raw = json.dumps(self.document, ensure_ascii=False, sort_keys=True).encode("utf-8")
        self.manifest["files"]["instructions.json"] = hashlib.sha256(raw).hexdigest()
        (self.resources / "instructions.json").write_bytes(raw)
        (self.resources / "manifest.json").write_text(json.dumps(self.manifest), encoding="utf-8")

    def set_text(self, collection: str, identity: str, language: str, text: str) -> None:
        entry = self.document[collection][identity][language]
        entry["text"] = text
        key = "text_sha256" if collection == "fragments" else "content_sha256"
        entry[key] = hashlib.sha256(text.encode("utf-8")).hexdigest()
        self.save()
