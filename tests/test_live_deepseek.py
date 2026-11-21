import os

import pytest

from paicode.agent.loop import AgentRunner
from paicode.core.stats import UsageStats
from paicode.providers.store import ProviderConfig


@pytest.mark.live
def test_live_deepseek_creates_file(tmp_path):
    api_key = os.getenv("DEEPSEEK_API_KEY", "")
    if not os.getenv("PAICODE_LIVE") or not api_key:
        pytest.skip("Set PAICODE_LIVE=1 and DEEPSEEK_API_KEY to run the live provider test.")

    root = tmp_path / "live"
    root.mkdir()
    provider = ProviderConfig(
        name="deepseek",
        base_url="https://api.deepseek.com/v1",
        api_keys=[api_key],
        model="deepseek-flash",
    )
    events = []
    runner = AgentRunner(
        root,
        provider,
        UsageStats(),
        rules=[],
        skills=[],
        emit=events.append,
        max_steps=6,
    )
    runner.run("Create live.txt containing exactly LIVE_DEEPSEEK, verify it, and finish.")
    assert (root / "live.txt").read_text(encoding="utf-8").strip() == "LIVE_DEEPSEEK"
