"""Bounded, read-only project discovery. No inferred material or mesh assignments."""

import hashlib
import json
import os
from pathlib import Path

from defusedxml import ElementTree as ET

from .config import Settings, scoped_path

ASSET_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tga", ".webp",
                    ".xmf", ".xrf", ".xsf", ".xaf", ".fbx", ".chkn", ".cfl"}
MARKERS = {"draft_properties.json", ".imvu", "index.xml"}
MAX_FILE = 64 * 1024 * 1024


def file_bytes(path: Path, limit=MAX_FILE) -> bytes:
    with path.open("rb") as handle:
        data = handle.read(limit + 1)
    if len(data) > limit:
        raise ValueError(f"File exceeds the {limit}-byte limit")
    return data


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def walk(root: Path, max_depth=5, max_entries=5000):
    count = 0
    for directory, dirs, files in os.walk(root, followlinks=False):
        current = Path(directory)
        dirs[:] = sorted(d for d in dirs if not d.startswith(".")
                         and not (current / d).is_symlink()
                         and not getattr(current / d, "is_junction", lambda: False)())
        if len(current.relative_to(root).parts) >= max_depth:
            dirs[:] = []
        count += len(files) + len(dirs) + 1
        if count > max_entries:
            raise ValueError("Scan limit reached; configure a smaller project root")
        yield current, sorted(files)


def list_projects(settings: Settings) -> dict:
    projects = []
    seen = set()
    for root in settings.project_roots:
        for directory, files in walk(root):
            if MARKERS.intersection(files) and directory not in seen:
                scoped_path(directory, settings.project_roots)
                seen.add(directory)
                projects.append({"path": str(directory), "name": directory.name,
                                 "markers": sorted(MARKERS.intersection(files))})
    return {"projects": projects, "count": len(projects),
            "note": "CHKN/CFL archives are assets, not expanded Studio draft folders."}


def inspect_project(settings: Settings, path: str) -> dict:
    project = scoped_path(path, settings.project_roots)
    if not project.is_dir() or not any((project / marker).is_file() for marker in MARKERS):
        raise ValueError("Expected a Studio project folder containing index.xml or draft metadata")
    assets = []
    for directory, files in walk(project, max_depth=3):
        for name in files:
            if Path(name).suffix.lower() not in ASSET_EXTENSIONS:
                continue
            asset = scoped_path(directory / name, settings.project_roots, file=True)
            assets.append({"path": str(asset), "relative_path": asset.relative_to(project).as_posix(),
                           "bytes": asset.stat().st_size, "extension": asset.suffix.lower()})
    metadata = {}
    for name in ("draft_properties.json", ".imvu"):
        if (project / name).is_file():
            candidate = scoped_path(project / name, settings.project_roots, file=True)
            raw = json.loads(file_bytes(candidate, 1024 * 1024))
            # Report known descriptive fields only. Never return account/session data.
            if isinstance(raw, dict):
                keys = {"name", "productname", "productid", "parentproductid", "producttype",
                        "description", "category", "rating", "gender"}
                metadata[name] = {k: v for k, v in raw.items() if k.lower() in keys
                                  and isinstance(v, (str, int, float, bool, type(None)))}
    index = project / "index.xml"
    components = []
    if index.is_file():
        index = scoped_path(index, settings.project_roots, file=True)
        document = ET.fromstring(file_bytes(index, 4 * 1024 * 1024))
        # Preserve the actual XML vocabulary and values; no schema conversion.
        nodes = list(document.iter())
        if len(nodes) > 20000:
            raise ValueError("index.xml exceeds the XML element limit")
        template = next((n for n in nodes if n.tag == "Template"), document)
        for child in list(template)[:250]:
            components.append({"tag": child.tag, "attributes": dict(child.attrib),
                               "text": (child.text or "").strip()[:500],
                               "children": [{"tag": n.tag, "attributes": dict(n.attrib),
                                             "text": (n.text or "").strip()[:500]}
                                            for n in list(child)[:100]]})
    return {"path": str(project), "metadata": metadata, "assets": assets,
            "index_components": components, "read_only": True,
            "note": "Only locally saved data; inherited and unsaved Studio state may differ."}
