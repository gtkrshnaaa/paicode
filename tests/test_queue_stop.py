from pathlib import Path

from paicode.providers.store import ProviderStore
from paicode.tui.app import PaiCodeApp
from paicode.tui.widgets.work_status import WorkStatus


class FakeRunner:
    def __init__(self):
        self.stopped = False

    def request_stop(self):
        self.stopped = True


async def test_prompt_queue_and_triple_escape(project: Path, config_home: Path):
    app = PaiCodeApp(project, ProviderStore())
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        status = app.query_one(WorkStatus)

        app.chat.begin_work()
        app.chat.set_queue(2)
        assert status.is_working
        assert status.queue_count == 2
        app.chat.end_work()
        assert not status.is_working
        app.chat.set_queue(0)

        app.busy = True
        app._start_prompt("queued expanded text", [], "queued display text")
        assert len(app._prompt_queue) == 1
        assert status.queue_count == 1
        app._cmd_queue("")
        app._cmd_queue("clear")
        assert app._prompt_queue == []
        assert status.queue_count == 0

        fake = FakeRunner()
        app._active_runner = fake
        app.busy = True
        await pilot.press("escape")
        await pilot.pause()
        assert fake.stopped
        app.busy = False
