"""通过 MCP 会话验证物化 schema 和可信工厂绑定。"""

from __future__ import annotations

import asyncio
import json

from mcp import Client
from support.materialization_workspace import (
    _result_text,
    _workspace,
)

from token_io_decoupling.server import create_tools_server


def test_worker_stdio_exposes_bounded_action_schema_and_applies_only_with_factory(
    tmp_path,
) -> None:
    """真实MCP入口保留有界物化schema；只有可信工厂配置的Worker操作才产生获准文件。"""
    path = "src/output.txt"
    project, artifacts, state, provider, preflight, grant_provider, config, materializer = (
        _workspace(tmp_path, [path])
    )
    materializer.close()
    server = create_tools_server(
        provider,
        compliance_service=preflight,
        output_materializer_config=config,
    )

    async def run() -> None:
        """通过同一真实会话核对准备、审阅、preflight与apply，以及过期授权后的拒绝。"""
        async with Client(server, mode="auto") as client:
            tools = {tool.name: tool for tool in (await client.list_tools()).tools}
            assert "materialize_decoupled_output" in tools
            description = tools["materialize_decoupled_output"].description or ""
            assert "1–16个" in description
            assert "全批次新鲜 preflight" in description
            assert "同服务协作锁" in description
            request_schema = tools["materialize_decoupled_output"].input_schema["properties"][
                "payload"
            ]["properties"]["request"]
            assert request_schema["discriminator"]["propertyName"] == "action"
            variants = request_schema["oneOf"]
            assert {variant["properties"]["action"]["const"] for variant in variants} == {
                "prepare",
                "inspect",
                "apply",
            }
            prepare_schema = next(
                variant
                for variant in variants
                if variant["properties"]["action"]["const"] == "prepare"
            )
            file_schema = prepare_schema["properties"]["files"]
            assert file_schema["minItems"] == 1
            assert file_schema["maxItems"] == 16
            template_schema = file_schema["items"]["properties"]["template"]
            assert {
                variant["properties"]["kind"]["const"] for variant in template_schema["oneOf"]
            } == {"literal_text", "json_document", "fact_markdown"}
            prepared_result = await client.call_tool(
                "materialize_decoupled_output",
                {
                    "payload": {
                        "request": {
                            "action": "prepare",
                            "files": [
                                {
                                    "path": path,
                                    "operation": "create",
                                    "baseline": {"state": "absent"},
                                    "template": {
                                        "kind": "literal_text",
                                        "text": "stdio result\n",
                                    },
                                }
                            ],
                        }
                    }
                },
            )
            assert not prepared_result.is_error
            prepared = json.loads(_result_text(prepared_result))
            apply_result = await client.call_tool(
                "materialize_decoupled_output",
                {
                    "payload": {
                        "request": {
                            "action": "apply",
                            "prepared_id": prepared["prepared_id"],
                            "expected_manifest_hash": prepared["manifest_sha256"],
                        }
                    }
                },
            )
            assert not apply_result.is_error
            applied = json.loads(_result_text(apply_result))
            assert applied["status"] == "applied"

    try:
        asyncio.run(run())
        assert (project / path).read_text() == "stdio result\n"
        assert any(artifacts.iterdir())
    finally:
        close = getattr(server, "_output_materializer", None)
        if close is not None:
            close.close()
        preflight.close()
