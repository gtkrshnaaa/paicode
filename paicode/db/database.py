import os
import shutil
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from .schema import MIGRATIONS
from .seed import seed_provider_presets


def database_path() -> Path:
    explicit = os.getenv("PAICODE_DB_PATH")
    if explicit:
        return Path(explicit).expanduser().resolve()
    override = os.getenv("PAICODE_STATE_DIR")
    if override:
        base = Path(override).expanduser().resolve()
    else:
        base = Path(os.getenv("XDG_STATE_HOME", str(Path.home() / ".local" / "state"))) / "paicode"
    return base / "paicode.db"


class Database:
    def __init__(self, path: Path | None = None):
        self.path = Path(path) if path else database_path()

    def _ensure_directory(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.chmod(self.path.parent, 0o700)
        except OSError:
            pass

    def _secure_files(self) -> None:
        for suffix in ("", "-wal", "-shm"):
            candidate = Path(str(self.path) + suffix)
            if candidate.exists():
                try:
                    os.chmod(candidate, 0o600)
                except OSError:
                    pass

    @contextmanager
    def connection(self):
        self._ensure_directory()
        conn = sqlite3.connect(self.path, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=10000")
        conn.execute("PRAGMA secure_delete=ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
            self._secure_files()

    def initialize(self) -> list[str]:
        self._ensure_directory()
        with self.connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS migrations (
                    version INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    applied_at TEXT NOT NULL
                )
                """
            )
            applied = {
                row["version"] for row in conn.execute("SELECT version FROM migrations").fetchall()
            }
            for migration in MIGRATIONS:
                if migration["version"] in applied:
                    continue
                conn.executescript(migration["sql"])
                conn.execute(
                    "INSERT INTO migrations (version, name, applied_at) VALUES (?, ?, ?)",
                    (
                        migration["version"],
                        migration["name"],
                        datetime.now().astimezone().isoformat(timespec="seconds"),
                    ),
                )
            seeded = seed_provider_presets(conn)
        self._secure_files()
        return seeded

    def reset(self) -> dict:
        self._ensure_directory()
        backup = None
        if self.path.exists():
            try:
                with self.connection() as conn:
                    conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            except sqlite3.DatabaseError:
                pass
            backup = self.path.with_name(
                f"{self.path.name}.bak-{datetime.now().strftime('%Y%m%d-%H%M%S-%f')}"
            )
            shutil.copy2(self.path, backup)
            try:
                os.chmod(backup, 0o600)
            except OSError:
                pass
        for suffix in ("", "-wal", "-shm"):
            candidate = Path(str(self.path) + suffix)
            if candidate.exists():
                candidate.unlink()
        seeded = self.initialize()
        return {
            "path": self.path,
            "backup": backup,
            "migrations": len(MIGRATIONS),
            "seeded": seeded,
        }

    def counts(self) -> dict[str, int]:
        tables = [
            "provider_presets",
            "providers",
            "provider_keys",
            "sessions",
            "session_messages",
            "session_transcript",
            "session_diffs",
        ]
        with self.connection() as conn:
            return {
                table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                for table in tables
            }
