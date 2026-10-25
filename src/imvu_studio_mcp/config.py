from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    project_roots: tuple[Path, ...] = ()
    asset_roots: tuple[Path, ...] = ()
    state_dir: Path = Path.home() / ".imvu-studio-mcp"
    enable_writes: bool = False
    enable_ui: bool = False
    cdp_port: int = 9222
    studio_exe: Path | None = None

    def __post_init__(self):
        for field in ("project_roots", "asset_roots"):
            roots = tuple(p.expanduser().resolve(strict=True) for p in getattr(self, field))
            if any(not p.is_dir() or p == Path(p.anchor) for p in roots):
                raise ValueError("Configure existing folders, not entire filesystem roots")
            object.__setattr__(self, field, roots)
        if not 1024 <= self.cdp_port <= 65535:
            raise ValueError("CDP port must be between 1024 and 65535")
        object.__setattr__(self, "state_dir", self.state_dir.expanduser().resolve())


def scoped_path(value: str | Path, roots: tuple[Path, ...], *, file=False) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        raise ValueError("An absolute path is required")
    path = path.resolve(strict=True)
    matching_roots = [root for root in roots if path.is_relative_to(root)]
    if not matching_roots:
        raise ValueError("Path is outside the configured roots")
    if file and not path.is_file():
        raise ValueError("Expected an existing file")
    root = max(matching_roots, key=lambda candidate: len(candidate.parts))
    if any(part.startswith(".") for part in path.relative_to(root).parts if part != ".imvu"):
        raise ValueError("Hidden folders and files are excluded")
    return path
