import asyncio
import json
import os
import sys
from pathlib import Path

import pytest
from mcp import Client
from mcp.client.stdio import StdioServerParameters

from imvu_studio_mcp.config import Settings
from imvu_studio_mcp.server import create_server
from imvu_studio_mcp.studio import Studio, is_studio_url


def payload(result):
    assert not result.is_error, result
    return result.structured_content or json.loads(result.content[0].text)


@pytest.mark.parametrize("mode", ["auto", "legacy"])
def test_real_stdio_roundtrip(workspace, mode):
    settings, draft, target, source = workspace

    async def run():
        parameters = StdioServerParameters(
            command=sys.executable,
            args=["-m", "imvu_studio_mcp", "--project-root", str(settings.project_roots[0]),
                  "--asset-root", str(settings.asset_roots[0]), "--state-dir", str(settings.state_dir),
                  "--enable-writes"],
            env={"PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src"),
                 "SYSTEMROOT": os.environ.get("SYSTEMROOT", "")})
        async with Client(parameters, read_timeout_seconds=20, mode=mode) as client:
            tools = await client.list_tools()
            assert len(tools.tools) == 17
            status = await client.call_tool("server_status", {})
            assert not status.is_error
            assert status.structured_content["version"] == "0.1.0"
            listing = await client.call_tool("projects_list", {})
            assert payload(listing)["count"] == 1
            image = await client.call_tool("texture_preview", {"path": str(source)})
            assert image.content[0].type == "image"
            assert image.content[0].mime_type == "image/png"
            plan = await client.call_tool("texture_replace_prepare", {"source": str(source), "target": str(target)})
            plan_id = payload(plan)["id"]
            applied = await client.call_tool("texture_replace_apply", {"plan_id": plan_id})
            assert payload(applied)["status"] == "applied"
            restored = await client.call_tool("texture_restore", {"plan_id": plan_id})
            assert payload(restored)["status"] == "restored"
            blocked = await client.call_tool("studio_inspect", {})
            assert blocked.is_error
            assert "disabled" in blocked.content[0].text
            bad_path = await client.call_tool("texture_inspect", {"path": str(settings.state_dir / "missing.png")})
            assert bad_path.is_error
            resources = await client.list_resources()
            assert str(resources.resources[0].uri) == "imvu-studio://workflow"

    asyncio.run(run())


def test_ui_identity_and_disabled_gate(tmp_path):
    assert is_studio_url("imvucreate://local/index.html?local=true")
    assert is_studio_url("imvucreate://local/home/home/")
    assert is_studio_url("imvucreate://local/product/example/")
    for url in ("https://imvu.com/index.html", "imvucreate://evil/index.html",
                "imvucreate://local/auth.html", "file:///index.html", "about:blank"):
        assert not is_studio_url(url)
    studio = Studio(Settings(state_dir=tmp_path))
    with pytest.raises(ValueError, match="disabled"):
        asyncio.run(studio.inspect())


def test_annotations_are_effective(tmp_path):
    async def run():
        async with Client(create_server(Settings(state_dir=tmp_path))) as client:
            tools = (await client.list_tools()).tools
            data = {tool.name: tool.annotations for tool in tools}
            assert data["project_inspect"].read_only_hint is True
            assert data["studio_click"].destructive_hint is True
            assert data["studio_click"].open_world_hint is True
    asyncio.run(run())
