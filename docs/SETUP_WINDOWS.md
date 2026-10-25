# Windows installation and connection

## Identify folders

Use Studio's **Open in Folder** control to locate the actual saved project folder.
Do not assume a fixed Documents path: OneDrive redirection and preferences can
change it. Identify a separate source-texture folder. Both must already exist.
The project root may be the whole Projects directory, an account folder, or one
draft. Prefer the narrowest useful scope. Do not rename Studio project folders.

Install using the root README. The `ui` extra adds Playwright; no separate browser
download is required. The package does not change any MCP client settings.

## Codex and other clients

Merge `examples/codex-config.toml` into your Codex user config or a trusted project
config, and edit its three paths. `command` and `args` follow the
[official Codex MCP guide](https://developers.openai.com/codex/mcp).
Restart/reconnect the server in your MCP settings after edits. Use an absolute
path to the isolated environment's Python; shell activation is unnecessary.

Use `examples/mcp-config.json` for clients accepting an `mcpServers` configuration.
Exact configuration shape depends on the client. Choose **local stdio**; there is
no hosted server URL or remote authentication flow.

## Studio connection

1. Save work and close an already running Studio manually.
2. Enable `--enable-ui` in the MCP process arguments.
3. Call `studio_launch`. It starts Studio with
   `--remote-debugging-address=127.0.0.1 --remote-debugging-port=9222`.
4. Wait for Studio to load, then call `studio_status`. Launching a process does
   not prove connection success; retry status after loading if needed.
5. Log in manually, then call `studio_inspect` and `studio_screenshot`.

Alternatively launch Studio yourself with those flags. Match `--cdp-port` if using
a different port. Pass `--studio-exe` with the installed `imvu-studio.exe` path if
automatic discovery fails.

The bridge accepts exactly one main window on the `imvucreate://local` origin,
at the initial index or a Home/product/derive route; it
rejects unrelated browser tabs and Studio's auth window. Each UI operation detaches
after completion without closing Studio. Do not use a daily browser's debug port.

## Texture replacement

Enable `--enable-writes` for apply/restore. Preparation creates local transaction
metadata even when project writes are disabled. The target must already exist
under a project root; the source must be under a project or source-asset root.
The filename is preserved; project metadata and material assignment are untouched.

Dimensions must match unless `allow_resize=true` was explicit during preparation.
The source's encoded image format must match the target extension. Convert source
images explicitly first if needed. Backups remain under the state directory.

## Troubleshooting

- **Connection refused:** Studio is loading, lacks the debugging flags, or uses a
  different port. Save/close it manually, then relaunch with debugging enabled.
- **No matching main window:** wrong app at that port, startup incomplete, or a
  Studio update changed the URL. Investigate rather than allowing arbitrary tabs.
- **Missing/ambiguous control:** inspect again; use exact accessible role/name.
  Unlabeled custom controls and native OS dialogs are not covered in v0.1.
- **No projects:** check the folder using Studio. Expanded drafts contain
  `index.xml`, `.imvu`, or `draft_properties.json`. CHKN/CFL archives are not parsed.
- **Scan limit:** configure a smaller account or draft folder as the root.
- **Changed-file conflict:** prepare a new plan from current files.
- **Windows pipe/temp errors:** use normal local user permissions for tests and
  allow the client to create a Python child process. Restrictive task sandboxes
  can block Windows MCP subprocess communication.
- **Interrupted replacement:** retain the transaction folder. Restore accepts
  `backed_up` plans after checking both current-file and backup hashes. It refuses
  corrupt backups and newer target edits. Do not edit journals/backups manually.

## Optional live smoke check

With Studio running in debugging mode, this checks the real stdio bridge:

```powershell
.\.venv\Scripts\python.exe scripts/smoke_studio.py
```

From Home with an empty product-search field, add `--exercise-controls` to fill a
synthetic search value, verify it, and restore the empty field. No project is
opened or edited. Reports contain connection/check status rather than account
details. This is optional and is not run by CI.
