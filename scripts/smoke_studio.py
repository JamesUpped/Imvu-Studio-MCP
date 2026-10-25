"""Opt-in local Studio smoke check. No project edits or account data are printed.

Run after starting Studio with the documented debugging flags. The optional
--exercise-controls fills the Home product search and clears it again, only when
uniquely identified and initially empty. Run from the Home window.
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

from mcp import Client
from mcp.client.stdio import StdioServerParameters


def payload(result):
    if result.is_error:
        raise RuntimeError(str(result.content))
    return result.structured_content or json.loads(result.content[0].text)


def textbox_block(tree: str, name: str) -> str:
    lines = tree.splitlines()
    index = next(i for i, line in enumerate(lines) if f'textbox "{name}"' in line)
    block = [lines[index]]
    for line in lines[index + 1:]:
        if not line.startswith("  "):
            break
        block.append(line)
    return "\n".join(block)


async def check(port: int, state_dir: Path, exercise: bool):
    params = StdioServerParameters(command=sys.executable, args=[
        "-m", "imvu_studio_mcp", "--enable-ui", "--cdp-port", str(port),
        "--state-dir", str(state_dir.resolve())])
    async with Client(params, read_timeout_seconds=25) as client:
        status = payload(await client.call_tool("studio_status"))
        if not status["connected"]:
            raise RuntimeError(status.get("connection_error", "Studio is not connected"))
        inspection = payload(await client.call_tool("studio_inspect"))
        screenshot = await client.call_tool("studio_screenshot")
        assert not screenshot.is_error and screenshot.content[0].type == "image"
        report = {"connected": True, "url": status["url"],
                  "accessibility_characters": len(inspection["accessibility_tree"]),
                  "screenshot_received": True, "search_roundtrip": "not requested"}
        if exercise:
            tree = inspection["accessibility_tree"]
            field = 'Please provide a valid product ID'
            block = textbox_block(tree, field)
            if ("/home/" not in status["url"] or not block.splitlines()[0].endswith(":")
                    or "- text:" in block):
                raise RuntimeError("Start on Home with an empty product search before exercising controls")
            query = "123456789"
            try:
                payload(await client.call_tool("studio_fill", {"role": "textbox", "name": field, "value": query}))
                changed = payload(await client.call_tool("studio_inspect"))
                assert query in textbox_block(changed["accessibility_tree"], field)
            finally:
                payload(await client.call_tool("studio_fill", {"role": "textbox", "name": field, "value": ""}))
            restored = payload(await client.call_tool("studio_inspect"))
            assert query not in textbox_block(restored["accessibility_tree"], field)
            report["search_roundtrip"] = "passed; original empty search restored"
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=9222)
    parser.add_argument("--state-dir", type=Path, default=Path.home() / ".imvu-studio-mcp")
    parser.add_argument("--exercise-controls", action="store_true")
    args = parser.parse_args()
    asyncio.run(check(args.port, args.state_dir, args.exercise_controls))
