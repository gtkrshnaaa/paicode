from pathlib import Path

from paicode.agent.events import TextDelta
from paicode.agents import BuildContract, MultiAgentRunner, WorkUnit
from paicode.core.stats import UsageStats
from paicode.providers.store import ProviderConfig


def _runner(project: Path, config_home: Path, base_url: str = "http://127.0.0.1:9/v1"):
    provider = ProviderConfig(
        name="fake",
        base_url=base_url,
        api_keys=["test-key"],
        model="fake-model",
    )
    runner = MultiAgentRunner(
        project,
        provider,
        UsageStats(),
        rules=[],
        skills=[],
        emit=lambda event: None,
        session_id="report-test",
    )
    runner.contract = BuildContract(
        feature="Report fallback",
        acceptance=["finish"],
        work_units=[WorkUnit("wu-1", "module", 2, ["module.py"])],
    )
    return runner


def test_lead_report_falls_back_when_provider_is_down(
    project: Path, config_home: Path
):
    events = []
    runner = _runner(project, config_home)
    runner.emit = events.append
    report = runner._final_report(None, stopped=False)
    runner._flush_events()
    assert "Lead report for" in report
    assert "Report fallback" in report
    assert any(isinstance(event, TextDelta) and "Lead report for" in event.text for event in events)


def test_stopped_lead_report_does_not_call_provider(
    project: Path, config_home: Path
):
    events = []
    runner = _runner(project, config_home)
    runner.emit = events.append
    report = runner._final_report(None, stopped=True)
    runner._flush_events()
    assert "Stopped by user" in report
    assert any(isinstance(event, TextDelta) and "Stopped by user" in event.text for event in events)
