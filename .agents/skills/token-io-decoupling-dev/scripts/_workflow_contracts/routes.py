"""路线模块清单、固定迁移 Hash 与仓库定位。"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]


ROUTES_DIR = Path("instruction-compiler/sources/skill/references/coding/layer-04-workflows")


MODULES_DIR = ROUTES_DIR / "modules"


MODULES = (
    "entry-readiness",
    "session-readiness",
    "work-definition",
    "single-execution",
    "delegated-execution",
    "verification-repair",
    "documentation",
    "delivery-acceptance",
)


ROUTE_MODULES = {
    "coding-single-agent": (
        "entry-readiness",
        "session-readiness",
        "work-definition",
        "single-execution",
        "verification-repair",
        "documentation",
        "delivery-acceptance",
    ),
    "coding-multi-agent": (
        "entry-readiness",
        "session-readiness",
        "work-definition",
        "delegated-execution",
        "verification-repair",
        "documentation",
        "delivery-acceptance",
    ),
}


MODULE_PREFIXES = {
    "entry-readiness": "ER",
    "session-readiness": "SR",
    "work-definition": "WD",
    "single-execution": "SE",
    "delegated-execution": "DE",
    "verification-repair": "VR",
    "documentation": "DOC",
    "delivery-acceptance": "DA",
}


MODULE_GRAPH_SHA256 = {
    "en": {
        "delegated-execution": "373cd76116cdbdad3a862a97a8221a5da51bc8a6a6d51db2a65675f8efbf4110",
        "delivery-acceptance": "114d90b56e06ce1cb9909b4d96709db532fbb01e96263412166e3ad878481145",
        "documentation": "c9070e292a599a7d4c2be5156ef4570082bfe7a042c0e65ff4597a09f6574714",
        "entry-readiness": "edeeb6e2db4f3f9bd0316532aaa00d52a1ab40a4bdd6f6d484e7126596745094",
        "session-readiness": "16f94918cc826fdf291d9102adc049acf5fca12d6778425d517845f257406252",
        "single-execution": "c8e13c6a23674d0743d8a19d0256c8623afb873f18e0e8a53c4042aebf104795",
        "verification-repair": "e1101b3f9ccb50347b5011bd134ba863fe47e96c05519f5593297a730f44333e",
        "work-definition": "df5ac02fb9814c1d7c4239255ae11632b86188d0e945ad20336f2c93a21eeea7",
    },
    "zh": {
        "delegated-execution": "9ea8f48b70ec5ed8af34127fcd89c4b56a91f816498769ec871409f4a9ffd441",
        "delivery-acceptance": "38cd9058f163cdce14984ef7076db774f5ac0d35cbe6186f4d9c41af74dfe16c",
        "documentation": "4efd99ed15b4f66fbe1e0d784222d8e7a50a3a55308821fcc4ee6e4f0c2de2fe",
        "entry-readiness": "dd9f41bc1fb7bd79c5076c3f9b458b7a25d077945d54c4cda877c2315d363460",
        "session-readiness": "a3756c195fef91d6e186c428fb1d030b0430d8dd0e677d10dd7da2af894245e1",
        "single-execution": "27a517874ef476a3b984a8f052ef9767311ab24547f16904b57edf570d9a2b66",
        "verification-repair": "c6ac131143c713a1a80daf5025e32d557e07dc1ab9b50dcce4850e59f40a7c0c",
        "work-definition": "85603bc72ab325515577e72be316797a608e09e05881c06a1ea3df2763b29cc8",
    },
}


MANIFEST_ROUTE_SHA256 = {
    "single-agent": "c51773c389de272b22a0e193368c00977800a08a4fbeafde7702c691b60a4177",
    "multi-agent": "7142e7d152c00fc3b359ed6bb38a2da36719a67b35c491a98738a2eddbb2c442",
}


TOP_PREFIXES = {"coding-single-agent": "SM", "coding-multi-agent": "MM"}


MIGRATION_MANIFEST = Path(
    ".agents/skills/token-io-decoupling-dev/references/migrations/workflow-module-migration.json"
)
