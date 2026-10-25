from typing import Any

from mcp.server import MCPServer
from mcp.server.mcpserver import Image
from mcp.types import ToolAnnotations

from . import __version__
from .config import Settings
from .errors import tool_errors
from .projects import inspect_project, list_projects
from .studio import Studio
from .textures import TextureService


def create_server(settings: Settings) -> MCPServer:
    settings.state_dir.mkdir(parents=True, exist_ok=True)
    textures = TextureService(settings)
    studio = Studio(settings)
    server = MCPServer(
        "IMVU Studio MCP", version=__version__,
        instructions=("Inspect before acting. Local project data may differ from unsaved Studio state. "
                      "Use exact accessible role/name pairs from studio_inspect. Studio UI actions can "
                      "change products, so act only within the user's request. Never infer material/mesh "
                      "IDs, replace skeletons, or replace body ID 2 for an add-on garment. Preview and "
                      "verify changes in Studio. Read project/texture files only in configured roots."))
    read = ToolAnnotations(read_only_hint=True, destructive_hint=False, open_world_hint=False)
    local_write = ToolAnnotations(read_only_hint=False, destructive_hint=False, open_world_hint=False)
    ui_write = ToolAnnotations(read_only_hint=False, destructive_hint=True, open_world_hint=True)

    @server.tool(annotations=read)
    @tool_errors
    def server_status() -> dict[str, Any]:
        """Show version, configured folder scopes, and enabled capabilities."""
        return {"version": __version__, "project_roots": [str(p) for p in settings.project_roots],
                "asset_roots": [str(p) for p in settings.asset_roots],
                "state_dir": str(settings.state_dir), "writes_enabled": settings.enable_writes,
                "ui_enabled": settings.enable_ui, "transport": "stdio"}

    @server.tool(annotations=read)
    @tool_errors
    def projects_list() -> dict[str, Any]:
        """Find saved Studio draft folders under the configured project roots (bounded scan)."""
        return list_projects(settings)

    @server.tool(annotations=read)
    @tool_errors
    def project_inspect(path: str) -> dict[str, Any]:
        """Read a saved project's asset inventory, descriptive metadata, and index.xml components."""
        return inspect_project(settings, path)

    @server.tool(annotations=read)
    @tool_errors
    def texture_inspect(path: str) -> dict[str, Any]:
        """Validate a scoped image and report dimensions, format, mode, hash, and size warnings."""
        return textures.inspect(path)

    @server.tool(annotations=read)
    @tool_errors
    def texture_preview(path: str) -> Image:
        """Return a PNG preview up to 1024 pixels wide/high without changing the source image."""
        return Image(data=textures.preview(path), format="png")

    @server.tool(annotations=local_write)
    @tool_errors
    def texture_replace_prepare(source: str, target: str, allow_resize: bool = False) -> dict[str, Any]:
        """Prepare a hash-bound replacement plan; does not change a project texture. Returns a plan ID."""
        return textures.prepare(source, target, allow_resize)

    @server.tool(annotations=local_write)
    @tool_errors
    def texture_replace_apply(plan_id: str) -> dict[str, Any]:
        """Apply a reviewed plan with an original backup; requires --enable-writes. Rejects stale plans."""
        return textures.apply(plan_id)

    @server.tool(annotations=local_write)
    @tool_errors
    def texture_restore(plan_id: str) -> dict[str, Any]:
        """Restore an original texture backup, refusing to overwrite subsequent edits. Requires writes enabled."""
        return textures.restore(plan_id)

    @server.tool(annotations=read)
    @tool_errors
    async def studio_status() -> dict[str, Any]:
        """Detect installed Studio versions and, if enabled, verify the local UI connection."""
        return await studio.status()

    @server.tool(annotations=ui_write)
    @tool_errors
    async def studio_launch() -> dict[str, Any]:
        """Start installed Studio with a loopback debugging port. Requires --enable-ui; does not stop existing Studio."""
        return await studio.launch()

    @server.tool(annotations=read)
    @tool_errors
    async def studio_inspect() -> dict[str, Any]:
        """Read the Studio main window accessibility tree. Requires UI enabled and Studio debugging active."""
        return await studio.inspect()

    @server.tool(annotations=read)
    @tool_errors
    async def studio_screenshot() -> Image:
        """Capture only the connected Studio main window as PNG. Requires UI enabled."""
        return Image(data=await studio.screenshot(), format="png")

    @server.tool(annotations=ui_write)
    @tool_errors
    async def studio_click(role: str, name: str) -> dict[str, Any]:
        """Click one uniquely identified Studio control by exact accessible role/name; inspect result afterward."""
        return await studio.click(role, name)

    @server.tool(annotations=ui_write)
    @tool_errors
    async def studio_fill(role: str, name: str, value: str) -> dict[str, Any]:
        """Fill one identified Studio textbox/spinbutton; password fields are excluded. Inspect before using."""
        return await studio.fill(role, name, value)

    @server.tool(annotations=ui_write)
    @tool_errors
    async def studio_select(name: str, label: str) -> dict[str, Any]:
        """Choose a label in a native Studio combobox identified by its exact accessible name."""
        return await studio.select(name, label)

    @server.tool(annotations=ui_write)
    @tool_errors
    async def studio_shortcut(action: str = "shortcut_guide") -> dict[str, Any]:
        """Open Studio's keyboard shortcut guide; this is the only supported keyboard action."""
        return await studio.shortcut(action)

    @server.tool(annotations=ui_write)
    @tool_errors
    async def studio_import_files(role: str, name: str, paths: list[str]) -> dict[str, Any]:
        """Click an observed file chooser control and select scoped assets. Does not confirm import settings."""
        return await studio.import_files(role, name, paths)

    @server.resource("imvu-studio://workflow")
    def workflow() -> str:
        """The server's safe local iteration workflow."""
        return ("1. Inspect server scopes and Studio. 2. Inspect the saved project and texture. "
                "3. Prepare a texture replacement; review both paths, hashes, dimensions, and warnings. "
                "4. Apply the returned plan ID, then review Studio's detected change and Preview. "
                "5. Save through an observed Studio control. 6. Restore by plan ID if needed. "
                "Never guess mesh/material IDs, skeletons, or scale. Preserve the body for add-on garments. "
                "UI control uses a local debugging connection and is optional. Log in manually. "
                "Submission/publishing requires an explicit user request; generic UI clicks can reach these controls.")

    return server
