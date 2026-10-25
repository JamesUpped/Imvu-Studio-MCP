"""Optional local Electron control through Chromium's standard debugging protocol.

Only rendered Studio UI is accessed. No application source modifications, private
JavaScript service calls, account-token extraction, or arbitrary code tools.
"""

import asyncio
import json
import os
import subprocess
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlsplit

from .config import Settings
from .projects import file_bytes


def is_studio_url(url: str) -> bool:
    parsed = urlsplit(url)
    # Studio changes history to its current route after loading index.html.
    return ((parsed.scheme, parsed.netloc) == ("imvucreate", "local")
            and (parsed.path == "/index.html" or parsed.path.startswith(("/home/", "/product/", "/derive/"))))


def installations() -> list[dict]:
    base = Path(os.environ.get("LOCALAPPDATA", "")) / "IMVU-Studio"
    found = []
    if base.is_dir():
        for package in base.glob("app-*/resources/app/package.json"):
            try:
                info = json.loads(file_bytes(package, 65536))
                exe = package.parents[2] / "imvu-studio.exe"
                if info.get("name") == "imvu-studio" and exe.is_file():
                    found.append({"version": info.get("version"), "executable": str(exe.resolve())})
            except (OSError, ValueError):
                continue
    return sorted(found, key=lambda entry: tuple(int(n) for n in entry["version"].split(".")
                                                if n.isdigit()), reverse=True)


class Studio:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.lock = asyncio.Lock()

    def check_enabled(self):
        if not self.settings.enable_ui:
            raise ValueError("Studio UI control is disabled; restart with --enable-ui")

    @asynccontextmanager
    async def connection(self):
        self.check_enabled()
        try:
            from playwright.async_api import async_playwright
        except ImportError as error:
            raise ValueError("Install the optional UI dependencies: pip install '.[ui]'") from error
        async with self.lock:
            async with async_playwright() as runtime:
                browser = await runtime.chromium.connect_over_cdp(
                    f"http://127.0.0.1:{self.settings.cdp_port}", timeout=8000)
                # Stopping this Playwright connection detaches without closing Studio.
                pages = [page for context in browser.contexts for page in context.pages
                         if is_studio_url(page.url)]
                if len(pages) != 1:
                    raise ValueError("Expected exactly one IMVU Studio main window at this debug port")
                page = pages[0]
                page.set_default_timeout(5000)
                yield page

    async def launch(self) -> dict:
        self.check_enabled()
        found = installations()
        exe = self.settings.studio_exe
        if exe is None:
            if not found:
                raise ValueError("Studio installation not found; supply --studio-exe")
            exe = Path(found[0]["executable"])
        exe = exe.resolve(strict=True)
        if exe.name.lower() != "imvu-studio.exe":
            raise ValueError("Expected the installed imvu-studio.exe")
        # Do not stop an existing app or alter its existing profile.
        flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        with (self.settings.state_dir / "launch.log").open("ab") as log:
            process = subprocess.Popen([str(exe), "--remote-debugging-address=127.0.0.1",
                                        f"--remote-debugging-port={self.settings.cdp_port}"],
                                       stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                                       creationflags=flags)
        return {"pid": process.pid, "executable": str(exe),
                "debug_endpoint": f"http://127.0.0.1:{self.settings.cdp_port}",
                "note": "Startup requested. Call studio_status to verify connection. If Studio was already running without debugging, close it manually and retry."}

    async def status(self) -> dict:
        result = {"installations": installations(), "ui_enabled": self.settings.enable_ui,
                  "connected": False, "debug_port": self.settings.cdp_port}
        if self.settings.enable_ui:
            try:
                async with self.connection() as page:
                    result.update(connected=True, title=await page.title(), url=page.url)
            except Exception as error:
                result["connection_error"] = str(error)[:600]
        return result

    @staticmethod
    def locator(page, role: str, name: str):
        allowed = {"button", "link", "textbox", "combobox", "checkbox", "radio",
                   "tab", "menuitem", "option", "spinbutton", "slider"}
        if role not in allowed or (not name and role != "combobox") or len(name) > 200:
            raise ValueError("Use a supported role and exact accessible name from studio_inspect")
        return page.get_by_role(role, name=name, exact=True)

    async def inspect(self) -> dict:
        async with self.connection() as page:
            snapshot = await page.locator("body").aria_snapshot(timeout=5000)
            return {"title": await page.title(), "url": page.url,
                    "accessibility_tree": snapshot[:40000], "truncated": len(snapshot) > 40000,
                    "note": "Use exact accessible names. Password values are not requested; visible account information may appear."}

    async def screenshot(self) -> bytes:
        async with self.connection() as page:
            return await page.screenshot(type="png", full_page=False, timeout=10000)

    async def click(self, role: str, name: str) -> dict:
        async with self.connection() as page:
            locator = self.locator(page, role, name)
            if await locator.count() != 1:
                raise ValueError("Control is missing or ambiguous; inspect Studio again")
            await locator.click()
            return {"status": "clicked", "role": role, "name": name,
                    "next": "Inspect Studio again to verify the resulting state."}

    async def fill(self, role: str, name: str, value: str) -> dict:
        if role not in {"textbox", "spinbutton"} or len(value) > 10000:
            raise ValueError("Fill requires a textbox or spinbutton and at most 10000 characters")
        async with self.connection() as page:
            locator = self.locator(page, role, name)
            if await locator.count() != 1:
                raise ValueError("Control is missing or ambiguous")
            if (await locator.get_attribute("type") or "").lower() == "password":
                raise ValueError("Sign in manually in Studio")
            await locator.fill(value)
            return {"status": "filled", "role": role, "name": name}

    async def select(self, name: str, label: str) -> dict:
        async with self.connection() as page:
            locator = self.locator(page, "combobox", name)
            if await locator.count() != 1:
                raise ValueError("Control is missing or ambiguous")
            if not await locator.is_visible():
                raise ValueError("Studio uses a hidden native select behind a custom dropdown; use visible observed controls")
            await locator.select_option(label=label)
            return {"status": "selected", "name": name, "label": label}

    async def shortcut(self, action: str) -> dict:
        # Only Studio's documented shortcut guide. Other actions use observed controls.
        if action != "shortcut_guide":
            raise ValueError("Supported action: shortcut_guide")
        async with self.connection() as page:
            await page.keyboard.press("Control+Shift+/")
            return {"status": "sent", "action": action}

    async def import_files(self, role: str, name: str, paths: list[str]) -> dict:
        from .config import scoped_path
        from .projects import ASSET_EXTENSIONS

        if not 1 <= len(paths) <= 20:
            raise ValueError("Import between 1 and 20 files at a time")
        files = [scoped_path(path, self.settings.asset_roots + self.settings.project_roots,
                             file=True) for path in paths]
        if any(path.suffix.lower() not in ASSET_EXTENSIONS for path in files):
            raise ValueError("Unsupported asset extension")
        async with self.connection() as page:
            locator = self.locator(page, role, name)
            if await locator.count() != 1:
                raise ValueError("Import control is missing or ambiguous")
            async with page.expect_file_chooser(timeout=5000) as event:
                await locator.click()
            chooser = await event.value
            await chooser.set_files([str(path) for path in files])
            return {"status": "files_selected", "count": len(files),
                    "next": "Inspect the import dialog and verify mesh/material IDs, skeleton, and scale before importing."}
