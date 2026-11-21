from pathlib import Path

from paicode.agent.attachments import ImageAttachment
from paicode.agent.events import ErrorEvent, Finished
from paicode.agent.loop import AgentRunner, compact_messages
from paicode.core.stats import UsageStats
from paicode.providers.store import ProviderConfig

from .fake_openai import FakeOpenAI, finish_chunk, text_chunk, usage_chunk


def responder(index, payload):
    return [text_chunk("Image received"), finish_chunk("stop"), usage_chunk(10, 2, 12)]


def provider(server) -> ProviderConfig:
    return ProviderConfig(
        name="fake",
        base_url=server.base_url,
        api_keys=["test-key"],
        model="fake-model",
    )


def test_runner_sends_multimodal_payload(project: Path):
    with FakeOpenAI(responder) as server:
        events = []
        runner = AgentRunner(project, provider(server), UsageStats(), [], [], events.append)
        image = ImageAttachment(token="[image-1]", mime="image/png", data=b"fake-png")
        runner.run("Describe this image.", images=[image])
        assert isinstance(events[-1], Finished)
        user_message = [message for message in server.requests[0]["messages"] if message["role"] == "user"][-1]
        assert user_message["content"][0] == {"type": "text", "text": "Describe this image."}
        assert user_message["content"][1]["type"] == "image_url"
        assert user_message["content"][1]["image_url"]["url"].startswith("data:image/png;base64,")


def test_runner_stops_before_the_next_request(project: Path):
    with FakeOpenAI(responder) as server:
        events = []
        runner = AgentRunner(project, provider(server), UsageStats(), [], [], events.append)
        runner.request_stop()
        runner.run("Do not run this.")
        assert isinstance(events[-1], ErrorEvent)
        assert events[-1].message == "Stopped by user."
        assert server.requests == []


def test_compact_messages_preserves_multimodal_user_content():
    content = [
        {"type": "text", "text": "Look at this."},
        {"type": "image_url", "image_url": {"url": "data:image/png;base64,AAAA"}},
    ]
    messages = [
        {"role": "system", "content": "system"},
        {"role": "user", "content": content},
    ]
    compacted = compact_messages(messages, max_chars=1_000_000)
    assert compacted[1]["content"] == content
