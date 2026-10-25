# Development notes

## 2026-10-24 — Full editor planning

The user requested a simplified, fully interactive editor whose UI and MCP can
edit all applicable Studio options on an imported mesh, synchronize into Studio,
and complete the upload. The user explicitly requested planning before further
implementation and confirmed **Studio settings first; geometry tools later**.
The preferred submission-versus-publication endpoint remains an open choice;
the plan covers both and proposes verified submission as the default until chosen.

The proposed architecture and release gates are in `EDITOR_PLAN.md`: one local
service and project model for the UI/MCP, a versioned capability registry, staged
changes with Studio readback, the actual Studio viewport, and a submission state
machine with receipt/PID verification and uncertain-outcome reconciliation.
Complete coverage must be measured per applicable control and Studio version;
the current 17 tools do not establish a feature-parity percentage.

Research used official Edit Mode, feature, material/transparency, scaling, Info,
import, submission and publication guidance, plus read-only local component
inspection. Submission, external product-page publishing and peer review are
distinct states. Account-gated controls and future Studio changes require
explicit compatibility coverage. No native app sources or user data were copied.

GitHub's initial workflow run `40158521870`, previously queued, is now reported
failed for all four OS/Python jobs with no recorded steps. Available job-log
retrieval returned not found; the cause is not established. Investigation is a
Phase 0 requirement. The prior local result remains 17 passed, 1 skipped; there
was no new runtime test run for this documentation-only update.

Only planning documentation, its README link and the changelog are changed. No
editor implementation, Studio mutation, product submission or paid operation
was performed in this turn. Implementation should start with the documented
Phase 0 once the user has reviewed the plan.

## 2026-10-24 — Initial implementation

### Requested outcome

Create an MCP server specifically for IMVU Studio, keep all MCP source and detailed
notes in `JamesUpped/Imvu-Studio-MCP`, and push commits. The requested first-version
priority is **Studio control plus project and texture tools**. Existing workspace
instructions normally favor Legacy Creator; this request explicitly targets
Studio. Existing artwork and asset projects remain outside this repository.

### Starting state and local findings

- The GitHub repository existed on `main`, containing a short README only.
- A separate clone was created inside the working directory; the parent workspace
  has unrelated assets and its own Git metadata. Only this nested clone is staged.
- Installed IMVU Studio version: **1.44.14**. Windows installation discovery reads
  the app's package name/version, not account/profile storage.
- Local read-only package inspection established `imvucreate://local/index.html`
  as the main window URL and `index.xml`, `draft_properties.json`, and `.imvu` as
  relevant saved-project files. These are implementation findings, not a promised
  public IMVU API contract.
- No documented public Studio automation API was found in the official material
  reviewed. Absence from those documents does not prove none exists. The chosen
  bridge uses Chromium CDP and observed UI controls rather than invented endpoints.
- Studio was already running without the debug endpoint during the first local
  connection attempt. A second launch reused the existing app; port 9222 refused
  connection. Work was not force-closed. Relaunch validation is tracked below.

### Decisions

- **Python 3.11+ and official MCP SDK 2.3.0.** The published SDK was checked instead
  of assuming the older FastMCP import still existed. v2 uses `MCPServer` and
  supports older MCP clients through protocol negotiation. A real stdio test is
  included; this does not claim every MCP client has been validated.
- **Local stdio.** Studio and local project files live on the user's machine.
  No public MCP HTTP server, hosted account proxy, or IMVU login-token handling.
- **Optional Playwright CDP.** Attach to Studio's Chromium; no separate browser
  download, installed-app modification, or private JavaScript service invocation.
- **Empty default filesystem scope and separate flags.** Users explicitly name
  folders, enable file replacements, and enable Studio control.
- **Original backups and hash-bound plans.** Source artwork remains unchanged;
  only an explicitly selected existing project texture can be replaced. Conflicts
  and newer edits are refused. Prepare/apply/restore is single-file, recoverable.
- **Saved-data inspection only.** No guessed material IDs, mesh IDs, export scale,
  skeleton names, or automatic changes to avatar body IDs. Inherited and unsaved
  state must be checked in Studio.

### Implemented scope

Seventeen tools cover status, project discovery/inspection, texture inspection and
image preview, replacement planning/application/restoration, Studio launch and
status, accessibility inspection, screenshot, click/fill/select, shortcut guide,
and file chooser selection. A workflow resource is included. See `TOOLS.md` for
arguments and operational limits, and `ARCHITECTURE.md` for recovery behavior.

### Validation record

- Isolated Windows Python 3.14 environment created; package installed editable
  with UI/test extras. Direct package versions are pinned in `pyproject.toml`.
- Synthetic asset tests verify saved IDs, metadata filtering, XML entity rejection,
  path traversal and hidden-file rejection, original-byte round trips, changed
  source/target conflicts, disabled writes, format/dimension checks, corrupted
  backup rejection, plan-ID validation, and bounded previews.
- Real stdio client test discovers 17 tools, calls status/list/image tools, applies
  and restores a synthetic texture, receives tool errors, and lists the resource.
- Initial suite: **15 passed, 1 skipped**. The skipped case requires Windows
  symlink creation privileges; Linux CI is configured to exercise that case.
- Initial test execution hit sandbox-specific temporary directory and Windows
  subprocess-pipe limitations. Running with normal local process permissions and
  repository-local test data resolved those environment issues.
- Studio installation discovery worked with the normal user environment. The task
  sandbox substitutes `LOCALAPPDATA`; an explicit executable path is available for
  unusual client environments.
- No live draft was imported, edited, saved, submitted, or published during these
  initial checks. User project appearance and texture reload need a live project
  check. CI configuration is supplied; remote CI results are recorded when known.

### Live Studio follow-up

After the user saved work and closed Studio, the server relaunched it with loopback
debugging and connected successfully to **1.44.14**. The running app changes its
main window from the initial index URL to `imvucreate://local/home/home/`; this
exposed a target-matching bug. Route-aware matching and regression coverage were
added while retaining the origin restriction and auth-window exclusion.

Read-only status, accessibility inspection, and a 305,614-byte PNG screenshot
succeeded against the actual app. The screenshot and accessibility output remain
local under the ignored state directory and are not committed.

The Home sort exposes an enhanced, hidden native select. The first control check
correctly failed visibility checks; the tool now explains this case explicitly
instead of timing out. No forced hidden-element interaction was added. The live
control check instead fills the observed visible product-search field through
the real MCP stdio client, observes the value, then clears it and confirms the
original empty search. Accessibility snapshots nest the value on a quoted text
child beneath the textbox; the smoke assertion was adjusted to read that block.

SDK v2 hides unexpected exception details from callers. Anticipated file/validation
failures are now translated to `ToolError` so users receive actionable messages
such as disabled capability or stale plan, without crash traces. Explicit legacy
negotiation and structured JSON output are covered by the protocol tests. A fault
injection test covers recovery after target replacement but before final journal
save. Final unit/integration result: **17 passed, 1 skipped**; dependency consistency
and whitespace checks also passed. The skipped Windows symlink case is described
above.

The completed live smoke script also passed through a real stdio MCP connection:
connected=true, accessibility snapshot received (10,092 characters), screenshot
image received, synthetic search value observed, and original empty search
restored. Studio remained open and no project was edited. The repository includes
the reusable opt-in check in `scripts/smoke_studio.py`.

### Follow-up work

Validate an actual draft's import → external texture replacement → reload →
Preview → Save workflow after Studio connects. Test labeled material controls,
custom dropdowns, snapshot actions, camera controls, and import dialogs. Add
version-tested semantic tools where generic accessible controls are insufficient.
Consider safe multi-texture batches only after single-file behavior is proven.

### Primary references reviewed

- [IMVU release notes](https://create.imvu.com/articles/studio/imvu-studio-release-notes/):
  external asset reload/Preview workflow, project-folder naming, and current
  texture warnings. Installed version 1.44.14 appears in the official release line.
- [Studio workflow session](https://create.imvu.com/articles/studio/learning-session-2-deep-dive-into-workflow/):
  textures edited externally inside project folders. Historical guidance; current
  installed behavior still needs a live project check.
- [Editing Classic projects](https://create.imvu.com/articles/classic/imvu-studio-editing-a-project-from-classic/):
  Studio imports CHKN via its user interface. No CHKN archive parser is claimed.
- [Studio shortcuts](https://create.imvu.com/articles/studio/imvu-studio-keyboard-shortcuts/):
  Windows shortcut-guide combination. The dedicated article was preferred over
  inconsistent older release-note shorthand.
- [Official MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
  and its v2 migration notes: `MCPServer`, tools/resources, stdio transport/client.
- [Playwright CDP reference](https://playwright.dev/python/docs/api/class-browsertype#browser-type-connect-over-cdp):
  attach to an existing Chromium instance and inspect its default context. CDP
  has lower fidelity than a full Playwright connection.
- [Codex MCP configuration](https://developers.openai.com/codex/mcp):
  local `command`, `args`, and timeout configuration used in the supplied example.
