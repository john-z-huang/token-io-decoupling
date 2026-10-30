import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/check_coding_document_migration.py"
SPEC = importlib.util.spec_from_file_location("coding_document_migration", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)
SECTIONS_SCRIPT = SCRIPT.with_name("check-layer-01-sections.py")
SECTIONS_SPEC = importlib.util.spec_from_file_location("layer_01_sections", SECTIONS_SCRIPT)
SECTIONS = importlib.util.module_from_spec(SECTIONS_SPEC)
assert SECTIONS_SPEC and SECTIONS_SPEC.loader
SECTIONS_SPEC.loader.exec_module(SECTIONS)


class CodingDocumentMigrationTests(unittest.TestCase):
    def make_valid_root(self) -> Path:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        moves = []
        for layer in MODULE.LAYERS:
            base = root / "docs/skill/references/coding" / layer
            deep = base / "category/nested"
            deep.mkdir(parents=True)
            self.write_navigation(base, root_owner=True, category=False)
            category = base / "category"
            category.mkdir(exist_ok=True)
            self.write_navigation(category, root_owner=False, category=True)
            self.write_navigation(deep, root_owner=False, category=False)
            for directory, name in ((base, "root-owner"), (deep, "deep-owner")):
                (directory / f"{name}.md").write_text("English owner", encoding="utf-8")
                (directory / f"{name}_zh_cn.md").write_text("中文所有者", encoding="utf-8")
            deep_target = deep / "deep-owner.md"
            moves.extend(
                [
                    {
                        "from": f"docs/skill/references/coding/{layer}/deep-owner.md",
                        "to": deep_target.relative_to(root).as_posix(),
                    },
                    {
                        "from": f"docs/skill/references/coding/{layer}/deep-owner_zh_cn.md",
                        "to": (deep / "deep-owner_zh_cn.md").relative_to(root).as_posix(),
                    },
                ]
            )
        self.write_index(root / "docs/skill/references/coding/layer-01-fundamental-concepts", ["root-owner.md"], ["category/INDEX.md"])
        self.write_index(root / "docs/skill/references/coding/layer-01-fundamental-concepts", ["root-owner_zh_cn.md"], ["category/INDEX_zh_cn.md"], zh=True)
        self.write_index(root / "docs/skill/references/coding/layer-01-fundamental-concepts/category", [], ["nested/INDEX.md"])
        self.write_index(root / "docs/skill/references/coding/layer-01-fundamental-concepts/category", [], ["nested/INDEX_zh_cn.md"], zh=True)
        self.write_index(root / "docs/skill/references/coding/layer-01-fundamental-concepts/category/nested", ["deep-owner.md"], [])
        self.write_index(root / "docs/skill/references/coding/layer-01-fundamental-concepts/category/nested", ["deep-owner_zh_cn.md"], [], zh=True)
        self.write_index(root / "docs/skill/references/coding/layer-02-workflow-concepts", ["root-owner.md"], ["category/INDEX.md"])
        self.write_index(root / "docs/skill/references/coding/layer-02-workflow-concepts", ["root-owner_zh_cn.md"], ["category/INDEX_zh_cn.md"], zh=True)
        self.write_index(root / "docs/skill/references/coding/layer-02-workflow-concepts/category", [], ["nested/INDEX.md"])
        self.write_index(root / "docs/skill/references/coding/layer-02-workflow-concepts/category", [], ["nested/INDEX_zh_cn.md"], zh=True)
        self.write_index(root / "docs/skill/references/coding/layer-02-workflow-concepts/category/nested", ["deep-owner.md"], [])
        self.write_index(root / "docs/skill/references/coding/layer-02-workflow-concepts/category/nested", ["deep-owner_zh_cn.md"], [], zh=True)
        docs = root / "docs"
        docs.mkdir(exist_ok=True)
        (docs / "coding-document-migration.json").write_text(
            json.dumps({"schema_version": 1, "document_moves": moves}), encoding="utf-8"
        )
        return root

    @staticmethod
    def write_navigation(directory: Path, *, root_owner: bool, category: bool) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "README.md").write_text(
            "[English](README.md) | [简体中文](README_zh_cn.md)\n\n[INDEX](INDEX.md)\n",
            encoding="utf-8",
        )
        (directory / "README_zh_cn.md").write_text(
            "[English](README.md) | [简体中文](README_zh_cn.md)\n\n[索引](INDEX_zh_cn.md)\n",
            encoding="utf-8",
        )
        (directory / "INDEX.md").write_text("[English](INDEX.md) | [简体中文](INDEX_zh_cn.md)\n", encoding="utf-8")
        (directory / "INDEX_zh_cn.md").write_text("[English](INDEX.md) | [简体中文](INDEX_zh_cn.md)\n", encoding="utf-8")

    @staticmethod
    def write_index(directory: Path, owners: list[str], children: list[str], *, zh: bool = False) -> None:
        index = directory / ("INDEX_zh_cn.md" if zh else "INDEX.md")
        links = [f"- [owner]({name})" for name in owners]
        links.extend(f"- [category]({name})" for name in children)
        with index.open("a", encoding="utf-8") as target:
            target.write("\n" + "\n".join(links) + "\n")

    def test_complete_valid_fixture_supports_nested_and_root_owners(self):
        root = self.make_valid_root()
        self.assertEqual(MODULE.validate(root), [])

    def test_layer_01_section_discovery_reaches_nested_owners(self):
        root = self.make_valid_root()
        base = root / "docs/skill/references/coding/layer-01-fundamental-concepts"
        discovered = SECTIONS.discover_owner_documents(base)
        self.assertIn(base / "root-owner.md", discovered)
        self.assertIn(base / "category/nested/deep-owner.md", discovered)
        self.assertFalse(any(path.name.startswith(("README", "INDEX")) for path in discovered))

    def test_missing_mirror_is_reported(self):
        root = self.make_valid_root()
        (root / "docs/skill/references/coding/layer-01-fundamental-concepts/category/nested/deep-owner_zh_cn.md").unlink()
        self.assertTrue(any("missing language pair" in e for e in MODULE.validate(root)))

    def test_missing_navigation_file_is_reported(self):
        root = self.make_valid_root()
        (root / "docs/skill/references/coding/layer-02-workflow-concepts/category/nested/README_zh_cn.md").unlink()
        self.assertTrue(any("navigation file missing" in e for e in MODULE.validate(root)))

    def test_index_must_list_direct_owner_and_child_directory(self):
        root = self.make_valid_root()
        index = root / "docs/skill/references/coding/layer-01-fundamental-concepts/category/nested/INDEX.md"
        index.write_text("[English](INDEX.md) | [简体中文](INDEX_zh_cn.md)\n", encoding="utf-8")
        self.assertTrue(any("index omits direct owner" in e for e in MODULE.validate(root)))

        index = root / "docs/skill/references/coding/layer-01-fundamental-concepts/INDEX.md"
        index.write_text(
            "[English](INDEX.md) | [简体中文](INDEX_zh_cn.md)\n"
            "- [root owner](root-owner.md)\n",
            encoding="utf-8",
        )
        self.assertTrue(any("index omits direct child directory" in e for e in MODULE.validate(root)))

    def test_incorrect_language_switch_is_reported(self):
        root = self.make_valid_root()
        path = root / "docs/skill/references/coding/layer-01-fundamental-concepts/category/README.md"
        path.write_text("[English](README.md) | [简体中文](INDEX_zh_cn.md)\n[INDEX](INDEX.md)\n", encoding="utf-8")
        self.assertTrue(any("incorrect or missing English language switch" in e for e in MODULE.validate(root)))

    def test_valid_navigation_labels_are_not_fixed(self):
        root = self.make_valid_root()
        readme = root / "docs/skill/references/coding/layer-01-fundamental-concepts/README.md"
        readme.write_text(
            "[English](README.md) | [简体中文](README_zh_cn.md)\n\n[Browse contents](INDEX.md)\n",
            encoding="utf-8",
        )
        index = root / "docs/skill/references/coding/layer-01-fundamental-concepts/INDEX.md"
        text = index.read_text(encoding="utf-8").replace("[owner](root-owner.md)", "[Root entry](root-owner.md)")
        index.write_text(text, encoding="utf-8")
        self.assertEqual(MODULE.validate(root), [])

    def test_pseudo_index_reference_is_rejected(self):
        root = self.make_valid_root()
        readme = root / "docs/skill/references/coding/layer-01-fundamental-concepts/README.md"
        readme.write_text("[English](README.md) | [简体中文](README_zh_cn.md)\n\nINDEX.md\n", encoding="utf-8")
        self.assertTrue(any("same-language index" in e for e in MODULE.validate(root)))

        index = root / "docs/skill/references/coding/layer-01-fundamental-concepts/INDEX.md"
        index.write_text(
            "[English](INDEX.md) | [简体中文](INDEX_zh_cn.md)\nroot-owner.md\n",
            encoding="utf-8",
        )
        self.assertTrue(any("index omits direct owner" in e for e in MODULE.validate(root)))

    def test_repeated_index_target_is_rejected(self):
        root = self.make_valid_root()
        index = root / "docs/skill/references/coding/layer-01-fundamental-concepts/INDEX.md"
        with index.open("a", encoding="utf-8") as target:
            target.write("- [another label](root-owner.md)\n")
        self.assertTrue(any("index repeats target" in e for e in MODULE.validate(root)))

    def test_invalid_migration_mapping_is_reported(self):
        root = self.make_valid_root()
        path = root / "docs/coding-document-migration.json"
        migration = json.loads(path.read_text(encoding="utf-8"))
        migration["document_moves"][0]["to"] = "../outside.md"
        path.write_text(json.dumps(migration), encoding="utf-8")
        self.assertTrue(any("unsafe migration mapping" in e for e in MODULE.validate(root)))

    def test_declared_task_plan_owner_rename_is_valid_in_both_languages(self):
        root = self.make_valid_root()
        layer = root / "docs/skill/references/coding/layer-01-fundamental-concepts"
        destination = layer / "execution-planning"
        destination.mkdir()
        self.write_navigation(destination, root_owner=False, category=False)
        self.write_index(layer, [], ["execution-planning/INDEX.md"])
        self.write_index(layer, [], ["execution-planning/INDEX_zh_cn.md"], zh=True)
        path = root / "docs/coding-document-migration.json"
        migration = json.loads(path.read_text(encoding="utf-8"))
        for old, new in MODULE.OWNER_RENAMES.items():
            target = root / new
            target.write_text("Task plan owner", encoding="utf-8")
            self.write_index(destination, [target.name], [], zh=target.name.endswith("_zh_cn.md"))
            migration["document_moves"].append({"from": old, "to": new})
        path.write_text(json.dumps(migration), encoding="utf-8")
        self.assertEqual(MODULE.validate(root), [])

    def test_undeclared_owner_rename_is_still_rejected(self):
        root = self.make_valid_root()
        path = root / "docs/coding-document-migration.json"
        migration = json.loads(path.read_text(encoding="utf-8"))
        migration["document_moves"][0]["from"] = (
            "docs/skill/references/coding/layer-01-fundamental-concepts/unapproved-owner.md"
        )
        path.write_text(json.dumps(migration), encoding="utf-8")
        self.assertTrue(any("changed owner filename" in e for e in MODULE.validate(root)))

    def test_malformed_migration_source_is_reported_without_crashing(self):
        root = self.make_valid_root()
        path = root / "docs/coding-document-migration.json"
        migration = json.loads(path.read_text(encoding="utf-8"))
        migration["document_moves"][0]["from"] = "owner.md"
        path.write_text(json.dumps(migration), encoding="utf-8")
        self.assertTrue(any("former Layer-01/02 root owner" in e for e in MODULE.validate(root)))

    def test_migration_record_does_not_require_every_current_owner(self):
        root = self.make_valid_root()
        path = root / "docs/coding-document-migration.json"
        path.write_text(json.dumps({"schema_version": 1, "document_moves": []}), encoding="utf-8")
        self.assertEqual(MODULE.validate(root), [])


if __name__ == "__main__":
    unittest.main()
