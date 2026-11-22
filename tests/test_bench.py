import json
from pathlib import Path

from paicode.bench import BenchTask, format_results, load_tasks, run_benchmark
from paicode.providers.store import ProviderStore

from .fake_openai import FakeOpenAI, finish_chunk, text_chunk, usage_chunk


def responder(index, payload):
    return [text_chunk("bench answer"), finish_chunk("stop"), usage_chunk(7, 3, 10)]


def test_benchmark_runs_in_isolated_copy_and_reports(project: Path, config_home: Path):
    manifest = project / "bench.json"
    manifest.write_text(
        json.dumps(
            {
                "tasks": [
                    {
                        "name": "smoke",
                        "prompt": "Inspect the project.",
                        "workspace": ".",
                        "verify": "python3 -c \"print('verified')\"",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    tasks = load_tasks(manifest)
    assert tasks[0].name == "smoke"
    with FakeOpenAI(responder) as server:
        store = ProviderStore()
        store.upsert("fake", server.base_url, api_key="test-key", model="fake-model")
        store.set_active("fake")
        results = run_benchmark(tasks, manifest.parent, ["plain"], repeat=1)
    assert len(results) == 1
    assert results[0].ok is True
    assert results[0].prompt_tokens == 7
    assert results[0].completion_tokens == 3
    assert "verified" in results[0].output
    text = format_results(results)
    assert "Passed 1/1 runs" in text
    assert "smoke" in text
