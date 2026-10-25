# Architecture and operational boundaries

## Layers

The MCP client starts `imvu-studio-mcp` as a local stdio child process. The official
MCP Python SDK owns protocol negotiation, input schemas, output handling, tool
errors, and transport. Normal output belongs on stderr; stdout is protocol-only.

`config.py` validates roots and resolves paths. `projects.py` performs bounded,
read-only discovery and parses descriptive local project data. `textures.py`
validates images and owns replacement transactions. `studio.py` handles optional
installation detection, launch, and an asynchronous Playwright CDP connection.
`server.py` exposes tools and the workflow resource; `__main__.py` parses flags.

No local HTTP MCP listener is started. Studio's optional debugging socket is a
separate loopback service owned by Studio. The MCP process connects only to
`http://127.0.0.1:PORT`, not a caller-supplied remote URL.

## Studio boundary

Installed Studio 1.44.14 is an Electron application. Read-only examination of its
local package metadata and entry-point behavior established the main window URL
and draft filenames. None of its proprietary source is copied into this repo.
The bridge uses Chromium's standard debugging protocol through Playwright to
access rendered controls; it does not call private IMVU JavaScript service objects.

Target selection requires exactly one `imvucreate://local` main page at the initial
index or a Home/product/derive route. Studio's history routing changes the URL
after startup; checking only `index.html` would reject a fully loaded window. The
authentication window and unrelated pages are rejected. This URL match is target
validation, not cryptographic authentication; a trusted local environment is
assumed. The debug endpoint is unauthenticated and must remain loopback-only.

The connection is scoped to a single operation. Exiting Playwright detaches;
`browser.close()` is intentionally not called on the attached app. UI requests
are serialized, but the user can still change Studio concurrently. Re-inspect
after actions. Native OS dialogs and unlabeled custom controls need future work.

## Filesystem boundary

There are no implicit roots. Existing folder paths are canonicalized at startup;
filesystem/drive roots are rejected. Every file access resolves the requested
path and checks containment. Hidden descendants are excluded except `.imvu`.
Hidden ancestors above an explicitly configured root are permitted. Symlinks that
resolve outside a scope are rejected; directory traversal skips symlinks/junctions.

Project inspection never rewrites `index.xml`, material IDs, mesh IDs, skeletons,
or asset names. Images are verified before decoding. Invalid formats, oversized
reads, decompression-bomb warnings, stale plans, and hash mismatches fail closed.

## Texture transactions

1. **prepared**: record canonical paths and original/replacement hashes. No target
   modification. Review the plan before apply.
2. **backed_up**: recheck both inputs, create `original.bin` exclusively, flush it,
   then persist this journal status.
3. **applied**: re-resolve and recheck the target, write a sibling temporary file,
   flush it, and use `os.replace` for atomic content replacement. Persist status.
4. **restored**: validate the backup and current target, then atomically restore
   original bytes. Preserve the journal and backup.

Atomic replacement prevents Studio from observing half-written texture contents.
This is a single-file operation, not a multi-file transaction. Existing file bytes
are preserved exactly in backup; filesystem ACLs and timestamps are not backed up.
The sibling temporary file inherits folder permissions. The journal uses atomic
replacement too. A crash after target replacement but before the applied status
can be recovered from the backed-up journal by hash verification.

Use one MCP process per project and avoid editing the same target in Studio or an
image editor during replacement. A process-local lock serializes transactions,
but it is not an OS lock against other programs or other MCP instances. A narrow
check/replace race remains possible if a separate process edits a file at exactly
that point. This is a local-user tool, not a hostile multi-user filesystem service.

## State and distribution

Transaction metadata, original bytes, and launch diagnostics remain local under
the configured state directory. No telemetry is implemented. The Python server
itself makes no IMVU account API requests; UI actions can make Studio use its own
network services. Only code, tests, examples, and notes are committed.

The package pins direct dependencies; optional UI and development extras are
separate. CI installs from `pyproject.toml`. The Windows Python 3.14 requirements
snapshot records the exact locally tested transitive versions; it is not a
cross-platform lockfile. Dependency updates require rerunning protocol and UI
checks, not merely changing pins.
