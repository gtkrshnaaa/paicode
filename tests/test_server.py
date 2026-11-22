import threading
from pathlib import Path

import pytest

from paicode.agent.events import Finished, TextDelta, ToolFinished, UsageUpdated
from paicode.core.stats import UsageStats
from paicode.providers.store import ProviderStore
from paicode.sdk import PaicodeClient
from paicode.server import create_server, event_to_dict

from .fake_openai import FakeOpenAI, finish_chunk, text_chunk, usage_chunk


@pytest.fixture
def server(config_home: Path):
    instance = create_server("127.0.0.1", 0, "test-token")
    thread = threading.Thread(target=instance.serve_forever, daemon=True)
    thread.start()
    try:
        yield instance
    finally:
        instance.shutdown()
        instance.server_close()
        thread.join(timeout=5)


def test_api_requires_token_and_reports_health(server, config_home: Path):
    host, port = server.server_address[:2]
    client = PaicodeClient(f"http://{host}:{port}", "wrong")
    with pytest.raises(RuntimeError):
        client.health()
    client = PaicodeClient(f"http://{host}:{port}", "test-token")
    assert client.health()["status"] == "ok"


def test_session_endpoints_and_console(server, project: Path, config_home: Path):
    host, port = server.server_address[:2]
    client = PaicodeClient(f"http://{host}:{port}", "test-token")
    assert client.sessions() == []
    created = client.create_session(str(project), "api-session")
    assert created["id"].startswith("s-")
    rows = client.sessions()
    assert rows[0]["title"] == "api-session"
    detail = client.session(created["id"])
    assert detail["workspace"] == str(project.resolve())

    import urllib.request

    request = urllib.request.Request(
        f"http://{host}:{port}/",
        headers={"Authorization": "Bearer test-token"},
    )
    with urllib.request.urlopen(request, timeout=5) as response:
        html = response.read().decode("utf-8")
    assert "Paicode Console" in html


def test_event_serialization():
    assert event_to_dict(TextDelta("hello")) == {"type": "TextDelta", "text": "hello"}
    finished = event_to_dict(Finished("done", 2))
    assert finished["type"] == "Finished"
    assert finished["steps"] == 2
    tool = event_to_dict(ToolFinished("read", True, "ok", "", ["a.py"], "read"))
    assert tool["changed"] == ["a.py"]
    stats = UsageStats(total_tokens=10, cost_usd=0.001)
    usage = event_to_dict(UsageUpdated(stats))
    assert usage == {"type": "UsageUpdated", "total_tokens": 10, "cost_usd": 0.001}


def test_prompt_endpoint_streams_events_and_saves_transcript(server, project: Path, config_home: Path):
    def responder(index, payload):
        return [text_chunk("api answer"), finish_chunk("stop"), usage_chunk(8, 2, 10)]

    with FakeOpenAI(responder) as fake:
        store = ProviderStore()
        store.upsert("fake", fake.base_url, api_key="test-key", model="fake-model")
        store.set_active("fake")
        host, port = server.server_address[:2]
        client = PaicodeClient(f"http://{host}:{port}", "test-token")
        created = client.create_session(str(project), "prompt-session")
        run = client.prompt(created["id"], "Answer through the API.")
        import urllib.request

        with urllib.request.urlopen(client.events_url(run["run_id"]), timeout=30) as response:
            body = response.read().decode("utf-8")
        assert "TextDelta" in body
        assert "api answer" in body
        detail = client.session(created["id"])
        assert detail["transcript"][-2]["kind"] == "user"
        assert detail["transcript"][-1]["kind"] == "assistant"
        assert detail["transcript"][-1]["text"] == "api answer"
