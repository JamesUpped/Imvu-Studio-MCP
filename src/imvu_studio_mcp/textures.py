import io
import json
import os
import re
import tempfile
import threading
import uuid
import warnings
from pathlib import Path

from PIL import Image

from .config import Settings, scoped_path
from .projects import digest, file_bytes

TEXTURES = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tga", ".webp"}
FORMATS = {".png": "PNG", ".jpg": "JPEG", ".jpeg": "JPEG", ".gif": "GIF",
           ".bmp": "BMP", ".tga": "TGA", ".webp": "WEBP"}
Image.MAX_IMAGE_PIXELS = 16_777_216


def image_info(data: bytes) -> dict:
    with warnings.catch_warnings():
        warnings.simplefilter("error", Image.DecompressionBombWarning)
        with Image.open(io.BytesIO(data)) as image:
            image.verify()
        with Image.open(io.BytesIO(data)) as image:
            image.load()
            width, height = image.size
            issues = []
            if width > 512 or height > 512:
                issues.append("Larger than 512 pixels; verify Studio's current texture warning and budget.")
            if any(n & (n - 1) for n in (width, height)):
                issues.append("Dimensions are not powers of two.")
            return {"width": width, "height": height, "mode": image.mode,
                    "format": image.format, "frames": getattr(image, "n_frames", 1),
                    "bytes": len(data), "sha256": digest(data), "warnings": issues}


def texture_path(value: str, roots: tuple[Path, ...]) -> Path:
    path = scoped_path(value, roots, file=True)
    if path.suffix.lower() not in TEXTURES:
        raise ValueError("Only supported texture image files are accepted")
    return path


def atomic_write(path: Path, data: bytes):
    descriptor, temporary = tempfile.mkstemp(prefix=".imvu-mcp-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


class TextureService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.lock = threading.Lock()

    @property
    def roots(self):
        return self.settings.project_roots + self.settings.asset_roots

    def inspect(self, path: str):
        file = texture_path(path, self.roots)
        return {"path": str(file), **image_info(file_bytes(file))}

    def preview(self, path: str) -> bytes:
        file = texture_path(path, self.roots)
        data = file_bytes(file)
        image_info(data)
        with Image.open(io.BytesIO(data)) as original:
            image = original.convert("RGBA")
            image.thumbnail((1024, 1024))
            output = io.BytesIO()
            image.save(output, format="PNG")
            return output.getvalue()

    def _directory(self, plan_id: str) -> Path:
        if not re.fullmatch(r"[0-9a-f]{32}", plan_id):
            raise ValueError("Invalid plan ID")
        return self.settings.state_dir / "transactions" / plan_id

    def _save(self, directory: Path, plan: dict):
        atomic_write(directory / "plan.json", json.dumps(plan, indent=2).encode())

    def prepare(self, source: str, target: str, allow_resize=False) -> dict:
        source_path = texture_path(source, self.roots)
        target_path = texture_path(target, self.settings.project_roots)
        if source_path == target_path:
            raise ValueError("Source and target must be different files")
        before = image_info(file_bytes(target_path))
        after = image_info(file_bytes(source_path))
        if after["format"] != FORMATS[target_path.suffix.lower()]:
            raise ValueError("Source image format must match the target extension; convert explicitly first")
        if not allow_resize and (before["width"], before["height"]) != (after["width"], after["height"]):
            raise ValueError("Dimensions differ; prepare with allow_resize=true to explicitly accept resizing")
        plan_id = uuid.uuid4().hex
        plan = {"id": plan_id, "status": "prepared", "source": str(source_path),
                "target": str(target_path), "before": before, "after": after,
                "allow_resize": allow_resize}
        directory = self._directory(plan_id)
        directory.mkdir(parents=True, exist_ok=False)
        self._save(directory, plan)
        return {**plan, "writes_enabled": self.settings.enable_writes,
                "next": "Apply this plan ID after reviewing the source, target, and hashes."}

    def _load(self, plan_id: str):
        directory = self._directory(plan_id)
        plan = json.loads(file_bytes(directory / "plan.json", 65536))
        if plan["id"] != plan_id:
            raise ValueError("Transaction ID mismatch")
        target = texture_path(plan["target"], self.settings.project_roots)
        return directory, plan, target

    def apply(self, plan_id: str) -> dict:
        if not self.settings.enable_writes:
            raise ValueError("File writes are disabled; restart with --enable-writes")
        with self.lock:
            directory, plan, target = self._load(plan_id)
            if plan["status"] != "prepared":
                raise ValueError("Only a prepared plan can be applied")
            source = texture_path(plan["source"], self.roots)
            original, replacement = file_bytes(target), file_bytes(source)
            if digest(original) != plan["before"]["sha256"] or digest(replacement) != plan["after"]["sha256"]:
                raise ValueError("Source or target changed since preparation; prepare a new plan")
            if image_info(replacement)["format"] != FORMATS[target.suffix.lower()]:
                raise ValueError("Replacement format does not match target")
            # Write a unique immutable backup before touching the destination.
            backup = directory / "original.bin"
            with backup.open("xb") as handle:
                handle.write(original)
                handle.flush()
                os.fsync(handle.fileno())
            plan["status"] = "backed_up"
            self._save(directory, plan)
            # Re-resolve and recheck immediately before replacement.
            checked = texture_path(str(target), self.settings.project_roots)
            if checked != target or digest(file_bytes(target)) != plan["before"]["sha256"]:
                raise ValueError("Target changed while backing up; original backup retained")
            atomic_write(target, replacement)
            plan["status"] = "applied"
            self._save(directory, plan)
            return {"id": plan_id, "status": "applied", "target": str(target),
                    "sha256": digest(replacement), "backup": str(backup),
                    "next": "In Studio, review the detected asset change, Preview, then Save."}

    def restore(self, plan_id: str) -> dict:
        if not self.settings.enable_writes:
            raise ValueError("File writes are disabled; restart with --enable-writes")
        with self.lock:
            directory, plan, target = self._load(plan_id)
            if plan["status"] not in {"applied", "backed_up"}:
                raise ValueError("This transaction has no active replacement to restore")
            current = digest(file_bytes(target))
            if current not in {plan["after"]["sha256"], plan["before"]["sha256"]}:
                raise ValueError("Target changed after replacement; refusing to overwrite newer work")
            original = file_bytes(directory / "original.bin")
            if digest(original) != plan["before"]["sha256"]:
                raise ValueError("Backup hash mismatch")
            if current != plan["before"]["sha256"]:
                atomic_write(target, original)
            plan["status"] = "restored"
            self._save(directory, plan)
            return {"id": plan_id, "status": "restored", "target": str(target),
                    "sha256": digest(original)}
