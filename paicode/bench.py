import json
import shutil
import subprocess
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from .agent.loop import AgentRunner
from .agents import MultiAgentRunner, SoloRunner
from .core.stats import UsageStats
from .providers.store import ProviderStore
from .rules.loader import load_rules
from .rules.skills import discover_skills


IGNORE = shutil.ignore_patterns(
    ".git", ".venv", "venv", "__pycache__", ".pytest_cache", "node_modules",
    "build", "dist", "target", ".mypy_cache", ".ruff_cache",
)


@dataclass
class BenchTask:
    name: str
    prompt: str
    workspace: str = "."
    verify: str = "true"
    max_steps: int = 0

    @classmethod
    def from_dict(cls, data: dict) -> "BenchTask":
        name = str(data.get("name", "")).strip()
        prompt = str(data.get("prompt", "")).strip()
        if not name or not prompt:
            raise ValueError("Each benchmark task requires name and prompt.")
        return cls(
            name=name,
            prompt=prompt,
            workspace=str(data.get("workspace", ".")),
            verify=str(data.get("verify", "true")),
            max_steps=max(0, int(data.get("max_steps", 0) or 0)),
        )


@dataclass
class BenchResult:
    task: str
    mode: str
    ok: bool
    duration_seconds: float
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float
    verify_exit: int
    output: str
    error: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def load_tasks(path: Path) -> list[BenchTask]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("tasks", payload) if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        raise ValueError("Benchmark manifest must contain a task list.")
    return [BenchTask.from_dict(row) for row in rows if isinstance(row, dict)]


def _prepare(task: BenchTask, manifest_dir: Path) -> Path:
    source = Path(task.workspace).expanduser()
    if not source.is_absolute():
        source = (manifest_dir / source).resolve()
    if not source.is_dir():
        raise FileNotFoundError(f"Workspace not found: {source}")
    target = Path(tempfile.mkdtemp(prefix="paicode-bench-"))
    shutil.copytree(source, target, dirs_exist_ok=True, ignore=IGNORE)
    return target


def run_task(task: BenchTask, mode: str, manifest_dir: Path) -> BenchResult:
    started = time.monotonic()
    workspace = _prepare(task, manifest_dir)
    stats = UsageStats()
    error = ""
    try:
        provider = ProviderStore().active()
        if provider is None:
            raise RuntimeError("No active provider.")
        rules = load_rules(workspace)
        skills = discover_skills(workspace)
        if mode == "team":
            runner = MultiAgentRunner(workspace, provider, stats, rules, skills, lambda event: None)
        elif mode == "solo":
            runner = SoloRunner(
                workspace, provider, stats, rules, skills, lambda event: None,
                max_steps=task.max_steps or None,
            )
        elif mode in {"plain", "single"}:
            runner = AgentRunner(
                workspace,
                provider,
                stats,
                rules,
                skills,
                lambda event: None,
                max_steps=task.max_steps,
            )
        else:
            raise ValueError(f"Unknown benchmark mode: {mode}")
        runner.run(task.prompt)
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
    try:
        completed = subprocess.run(
            task.verify,
            shell=True,
            cwd=str(workspace),
            capture_output=True,
            text=True,
            timeout=300,
        )
        verify_exit = completed.returncode
        verify_output = ((completed.stdout or "") + (completed.stderr or "")).strip()[:20_000]
    except subprocess.TimeoutExpired:
        verify_exit = 124
        verify_output = "verification timed out"
    duration = time.monotonic() - started
    return BenchResult(
        task=task.name,
        mode=mode,
        ok=verify_exit == 0 and not error,
        duration_seconds=round(duration, 3),
        prompt_tokens=stats.prompt_tokens,
        completion_tokens=stats.completion_tokens,
        cost_usd=round(stats.cost_usd, 6),
        verify_exit=verify_exit,
        output=verify_output,
        error=error,
    )


def run_benchmark(
    tasks: list[BenchTask],
    manifest_dir: Path,
    modes: list[str],
    repeat: int = 1,
) -> list[BenchResult]:
    results = []
    for task in tasks:
        for mode in modes:
            for _ in range(max(1, repeat)):
                results.append(run_task(task, mode, manifest_dir))
    return results


def format_results(results: list[BenchResult]) -> str:
    lines = [
        "MODE    TASK                           OK    SECONDS   TOKENS   COST",
        "------  -----------------------------  ----  --------  -------  -------",
    ]
    for row in results:
        lines.append(
            f"{row.mode:<7} {row.task[:29]:<29}  {'yes' if row.ok else 'no ':<4}  "
            f"{row.duration_seconds:>8.2f}  {row.prompt_tokens + row.completion_tokens:>7}  "
            f"${row.cost_usd:>6.4f}"
        )
    passed = sum(1 for row in results if row.ok)
    lines.append(f"\nPassed {passed}/{len(results)} runs.")
    return "\n".join(lines)
