import json

from paicode.providers.client import ProviderClient
from paicode.providers.store import ProviderConfig

from .fake_openai import FakeOpenAI, finish_chunk, text_chunk, tool_chunk, usage_chunk


def responder(index, payload):
    return [
        text_chunk("Hello"),
        tool_chunk("call_1", "write", json.dumps({"path": "hello.txt", "content": "LIVE"})),
        finish_chunk("tool_calls"),
        usage_chunk(10, 5, 15),
    ]


def test_stream_assembles_text_tools_and_usage():
    with FakeOpenAI(responder) as server:
        provider = ProviderConfig(
            name="fake",
            base_url=server.base_url,
            api_keys=["test-key"],
            model="fake-model",
        )
        seen = []
        result = ProviderClient(provider).stream(
            [{"role": "user", "content": "hi"}],
            tools=[],
            on_text=seen.append,
        )
        assert seen == ["Hello"]
        assert result.text == "Hello"
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0].name == "write"
        assert json.loads(result.tool_calls[0].arguments)["path"] == "hello.txt"
        assert result.usage.prompt_tokens == 10
        assert result.usage.completion_tokens == 5
        assert result.usage.total_tokens == 15
        assert result.finish_reason == "tool_calls"


def test_list_models_uses_openai_compatible_endpoint():
    with FakeOpenAI(responder, model_ids=["alpha", "beta"]) as server:
        provider = ProviderConfig(
            name="fake",
            base_url=server.base_url,
            api_keys=["test-key"],
            model="alpha",
        )
        assert ProviderClient(provider).list_models() == ["alpha", "beta"]
