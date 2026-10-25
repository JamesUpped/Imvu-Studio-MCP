# Tool reference — v0.1.0

All filesystem paths are absolute. Call `server_status` to inspect the effective
scopes and flags. Errors are returned as MCP tool errors. Descriptive tool data is
available as JSON text and structured output; image tools return MCP image blocks.

## Server and projects

- `server_status()` — version, roots, state directory, capability flags, transport.
- `projects_list()` — discover expanded drafts beneath configured project roots.
  Scans at most five directory levels and 5,000 entries per root. Hidden folders,
  directory symlinks, and Windows junctions are not traversed.
- `project_inspect(path)` — local asset inventory, selected descriptive metadata,
  and saved `index.xml` component data. Scans assets three levels deep. Reports
  actual saved identifiers; does not assign IDs or resolve remote inheritance.
  XML is parsed with external entities disabled. Metadata reads are capped at
  1 MiB, XML at 4 MiB, with a 20,000-element ceiling. Component summaries are
  bounded to 250 direct components and 100 children each.

## Textures

- `texture_inspect(path)` — size, mode, format, frames, SHA-256, and warnings.
  PNG/JPEG/GIF/BMP/TGA/WebP are supported. Reads are limited to 64 MiB per image;
  Pillow's decompression protections are enabled. Warnings cover dimensions above
  512 and dimensions that are not powers of two; these are guidance, not a claim
  that every Studio product has an identical hard limit.
- `texture_preview(path)` — PNG preview limited to 1024 × 1024 while preserving
  aspect ratio. The source is unchanged; animated images preview the first frame.
- `texture_replace_prepare(source, target, allow_resize=false)` — persist a plan
  containing both hashes and image properties. The target is not changed. Encoded
  format must match the target extension; resizing requires explicit acceptance.
- `texture_replace_apply(plan_id)` — requires `--enable-writes`; recheck source
  and target hashes, write an immutable original backup, journal the backup,
  then atomically replace the existing target and mark the plan applied.
- `texture_restore(plan_id)` — requires writes; verify original backup integrity
  and restore only if the target still matches this transaction's replacement or
  original. Reject newer edits. Repeated application/restoration is rejected.

Preparation returns the plan ID. Each plan lives under
`STATE_DIR/transactions/ID/plan.json`; original bytes live beside it in
`original.bin`. Keep the ID and state directory to retain recovery access. A new
plan does not overwrite or delete an old backup.

## Studio control

Every UI tool requires `--enable-ui` and the optional `ui` dependency. `studio_status`
can still detect installed versions when UI control is disabled.

- `studio_status()` — installation discovery and current local connection check.
- `studio_launch()` — start the installed app with loopback debugging. Returns a
  startup request and process ID, not a claim that the UI is ready.
- `studio_inspect()` — main-window accessibility snapshot, capped at 40,000
  characters. Re-observe after actions. Visible account details can appear.
- `studio_screenshot()` — current Studio main-window viewport, returned as PNG.
- `studio_click(role, name)` — click one exact, uniquely matched accessible control.
- `studio_fill(role, name, value)` — fill an exact textbox/spinbutton, maximum
  10,000 characters. Password fields are excluded. Sign in manually in Studio.
- `studio_select(name, label)` — choose a label on a native HTML select/combobox.
  Custom dropdown menus may need separately observed clicks.
- `studio_shortcut(action="shortcut_guide")` — send only the documented Windows
  shortcut-guide key combination, Control + Shift + /. Other keys are not exposed.
- `studio_import_files(role, name, paths)` — click a uniquely identified control
  that opens a file chooser, then select 1–20 scoped assets. Supported image
  extensions plus XMF/XRF/XSF/XAF/FBX/CHKN/CFL are allowed. Review the resulting
  import UI and settings; selection is not proof of import success.

Click/import roles: button, link, textbox, combobox, checkbox, radio, tab, menuitem,
option, spinbutton, slider. Names must be exact and at most 200 characters. An
empty name is allowed only for a uniquely identified combobox. Hidden enhanced
selects are rejected explicitly; use observed visible custom controls instead.
Missing or ambiguous targets fail instead of clicking a guessed match.

UI calls are serialized and time-bounded. No arbitrary JavaScript execution,
browser navigation, terminal execution, cookie extraction, or network API tools
are exposed. This does not prevent a generic UI click from reaching Studio's
Submit/Publish controls: those actions require explicit user intent from the MCP
caller. UI writes are independent of the texture-write flag.

## Resource

`imvu-studio://workflow` provides the recommended inspect → plan → apply → Preview
→ Save → restore workflow and IMVU body/skeleton preservation guidance.
