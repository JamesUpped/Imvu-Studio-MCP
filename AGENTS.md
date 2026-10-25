# IMVU Studio MCP development

This repository contains the MCP server and its documentation only. Do not commit
private Studio projects, account data, logs, credentials, proprietary application
sources, textures, avatar samples, or generated backups/screenshots.

Preserve source assets. Project metadata, skeletons, material IDs, mesh IDs, scale,
and export settings must not be guessed or silently rewritten. Add-on garments
must preserve the avatar body and underlying clothing, including upper-body ID 2.
Studio control is the requested target; do not assume Legacy and Studio features
or limits are interchangeable.

Use the official MCP SDK. Keep stdout exclusively for MCP protocol messages.
Use scoped paths and conflict detection for writes. Test via a real stdio client
before committing. Record capabilities, limitations, sources, and verification in
docs/DEVELOPMENT_NOTES.md. Version changes in CHANGELOG.md. Never force-push.
