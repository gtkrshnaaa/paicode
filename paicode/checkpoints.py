import hashlib
import json
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from .settings import state_dir


@dataclass
class Checkpoint:
    id: str
    created_at: str
    files: list[dict] = field(default_factory=list)


class CheckpointStore:
    def __init__(self, root: Path):
        self.root = Path(root).resolve()
        digest = hashlib.sha1(str(self.root).encode("utf-8")).hexdigest()[:12]
        self.base = state_dir() / "checkpoints" / digest

    def _relative(self, path: Path) -> str:
        return str(path.resolve().relative_to(self.root)).replace("\\", "/")

    def capture(self, paths: list[Path]) -> Checkpoint | None:
        files = []
        for path in paths:
            try:
                relative = self._relative(path)
            except ValueError:
                continue
            entry = {"path": relative, "existed": path.is_file()}
            if entry["existed"]:
                entry["size"] = path.stat().st_size
            files.append(entry)
        if not files:
            return None
        checkpoint = Checkpoint(
            id=datetime.now().strftime("%Y%m%d-%H%M%S-%f-") + uuid4().hex[:6],
            created_at=datetime.now().astimezone().isoformat(timespec="seconds"),
            files=files,
        )
        folder = self.base / checkpoint.id
        folder.mkdir(parents=True, exist_ok=True)
        for entry in files:
            if not entry["existed"]:
                continue
            source = self.root / entry["path"]
            target = folder / "files" / entry["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        (folder / "manifest.json").write_text(json.dumps(checkpoint.__dict__, indent=2), encoding="utf-8")
        return checkpoint

    def list(self, limit: int = 20) -> list[Checkpoint]:
        if not self.base.is_dir():
            return []
        rows = []
        for folder in sorted(self.base.iterdir(), reverse=True):
            manifest = folder / "manifest.json"
            if not manifest.is_file():
                continue
            try:
                payload = json.loads(manifest.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            rows.append(
                Checkpoint(
                    id=str(payload.get("id", folder.name)),
                    created_at=str(payload.get("created_at", "")),
                    files=list(payload.get("files", [])),
                )
            )
            if len(rows) >= limit:
                break
        return rows

    def restore(self, checkpoint_id: str = "") -> tuple[Checkpoint | None, list[str]]:
        checkpoints = self.list(limit=200)
        if not checkpoints:
            return None, []
        target = None
        wanted = "" if checkpoint_id == "latest" else checkpoint_id
        for checkpoint in checkpoints:
            if not wanted or checkpoint.id.startswith(wanted):
                target = checkpoint
                break
        if target is None:
            return None, []
        folder = self.base / target.id
        restored = []
        for entry in target.files:
            relative = str(entry.get("path", ""))
            if not relative:
                continue
            destination = (self.root / relative).resolve()
            try:
                destination.relative_to(self.root)
            except ValueError:
                continue
            if entry.get("existed"):
                backup = folder / "files" / relative
                if not backup.is_file():
                    continue
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(backup, destination)
            elif destination.exists():
                destination.unlink()
            restored.append(relative)
        return target, restored
