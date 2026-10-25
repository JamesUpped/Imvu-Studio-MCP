# IMVU Studio MCP

A local Model Context Protocol server for **IMVU Studio on Windows**: project
inspection, texture validation and previews, reversible texture replacement, and
optional control of Studio's Electron window. Community software, not an official
IMVU integration. Version **0.1.0**.

## Capabilities

- Detect Studio and read its window accessibility tree or capture a screenshot.
- Click uniquely identified controls, fill fields, choose native dropdown options,
  and select scoped asset files in a Studio import file chooser.
- Discover saved drafts and inspect local assets, descriptive metadata, and
  `index.xml` components, including saved material and mesh information.
- Validate image dimensions, format, mode, byte size, and SHA-256; return previews.
- Prepare texture replacement plans, reject changed inputs, back up original
  bytes, replace atomically, and restore without overwriting newer edits.

This version does not generate geometry/images, infer export settings, rewrite
project metadata, or provide a hosted service. UI control uses observed accessible
controls; Studio updates and unlabeled custom controls can affect it. Logged-in
project workflows require live validation before unattended use.

## Install

Requires Python 3.11+; tested locally with Python 3.14. Windows is the supported
Studio control platform; file tools also work on other platforms.

```powershell
git clone https://github.com/JamesUpped/Imvu-Studio-MCP.git
cd Imvu-Studio-MCP
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e '.[ui,dev]'
```

No Playwright browser download is required: UI control attaches to Studio's own
Chromium instance. Omit the `ui` extra for file tools only.

## Connect an MCP client

See [Windows setup](docs/SETUP_WINDOWS.md), the
[Codex example](examples/codex-config.toml), and the
[generic stdio example](examples/mcp-config.json). Replace example paths with
existing folders. Use the isolated environment's absolute Python path in the
client configuration.

```powershell
.\.venv\Scripts\python.exe -m imvu_studio_mcp `
  --project-root 'C:\Your\IMVU Studio Projects' `
  --asset-root 'C:\Your\Texture Sources' `
  --enable-ui --enable-writes
```

The process serves MCP over stdin/stdout and waits for a client. Folder scopes
are empty by default. Repeat folder arguments as needed. Studio control and file
replacement each require their own explicit flag.

## First workflow

1. Call `server_status`, then `studio_status`.
2. If needed, call `studio_launch`, wait for startup, and check status again.
   A previously running Studio may need to be saved and closed manually first.
3. Call `studio_inspect` and `studio_screenshot`. Log in manually if required.
4. Find the saved project with `projects_list`, then call `project_inspect`.
5. Inspect both textures, then call `texture_replace_prepare` with absolute source
   and target paths. Review the returned dimensions, warnings, and hashes.
6. Apply that plan ID with `texture_replace_apply`. Review Studio's asset reload,
   Preview the result, and Save using controls observed in the current window.
7. To undo the replacement, call `texture_restore` with the same plan ID.

IMVU documents external asset updates followed by Preview in Studio. Preserve
asset filenames and Studio project-folder names. See the development notes for
sources and version-specific findings.

## Documentation and testing

- [Windows setup](docs/SETUP_WINDOWS.md)
- [Tool reference](docs/TOOLS.md)
- [Architecture, boundaries, and recovery](docs/ARCHITECTURE.md)
- [Detailed notes and validation status](docs/DEVELOPMENT_NOTES.md)
- [Changelog](CHANGELOG.md)

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Tests use synthetic assets. The integration test launches the real server through
the official MCP stdio client, discovers tools, receives image content, and
applies/restores a test texture. CI is configured for Windows and Linux.

## Local access and data

Reads are limited to configured project/source folders. Backups and transaction
plans live under `~/.imvu-studio-mcp`, or `--state-dir`; keep this outside project
roots. Backups are retained. The server does not need account credentials and
does not read Studio cookies or authentication storage. Sign in through Studio.

The optional loopback debugging endpoint has no authentication; local programs
may reach it while enabled. Use a trusted machine and close the debugging-enabled
Studio session when finished. The MCP server is stdio-only. Generic UI clicks can
reach Save, Submit, and other consequential controls; callers must stay within
the user's authorized task. `--enable-writes` gates file replacement, not UI edits.

Only MCP code and notes belong in this repository. Private projects, artwork,
account data, screenshots, backups, and IMVU application source are excluded.
