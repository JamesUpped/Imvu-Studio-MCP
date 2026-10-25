import argparse
import sys
from pathlib import Path

from . import __version__
from .config import Settings
from .server import create_server


def main():
    parser = argparse.ArgumentParser(description="Local MCP server for IMVU Studio")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--project-root", type=Path, action="append", default=[],
                        help="Existing Studio projects folder; repeat for more folders")
    parser.add_argument("--asset-root", type=Path, action="append", default=[],
                        help="Existing source assets folder; repeat for more folders")
    parser.add_argument("--state-dir", type=Path, default=Path.home() / ".imvu-studio-mcp")
    parser.add_argument("--enable-writes", action="store_true")
    parser.add_argument("--enable-ui", action="store_true")
    parser.add_argument("--cdp-port", type=int, default=9222)
    parser.add_argument("--studio-exe", type=Path)
    args = parser.parse_args()
    try:
        settings = Settings(tuple(args.project_root), tuple(args.asset_root), args.state_dir,
                            args.enable_writes, args.enable_ui, args.cdp_port, args.studio_exe)
        create_server(settings).run(transport="stdio")
    except (ValueError, OSError) as error:
        print(f"IMVU Studio MCP: {error}", file=sys.stderr)
        raise SystemExit(2) from error


if __name__ == "__main__":
    main()
