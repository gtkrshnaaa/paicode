from datetime import datetime

from textual.app import ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.widgets import Static
from rich.text import Text

from ...agents.roles import ROSTER

SHORT_ROLE = {
    1: "LEAD", 2: "FRONTEND", 3: "UI", 4: "DESIGN", 5: "STATE", 6: "API",
    7: "BACKEND", 8: "DOMAIN", 9: "DATABASE", 10: "AUTH", 11: "VALIDATION",
    12: "TEST ARCH", 13: "TEST", 14: "INTEGRATION", 15: "A11Y", 16: "PERF",
    17: "DEVOPS", 18: "DOCS", 19: "DATA", 20: "QUALITY", 21: "OBSERVE",
    22: "VALIDATOR",
}


class AgentCard(Static):
    MAX_TURNS = 6

    def __init__(self, agent_id: int, role: str):
        super().__init__("", classes="agent-card")
        self.agent_id = agent_id
        self.role = role
        self.turns: list[dict] = []
        self.status = "idle"
        self._render_card()

    def set_status(self, status: str) -> None:
        self.status = status or "idle"
        self._render_card()

    def add_action(self, kind: str, detail: str, status: str = "running", timestamp: str = "") -> None:
        self.turns.append(
            {
                "kind": kind,
                "detail": (detail or "").splitlines()[0][:90],
                "status": status,
                "timestamp": timestamp or datetime.now().strftime("%H:%M:%S"),
            }
        )
        self.turns = self.turns[-self.MAX_TURNS :]
        self.status = status if status in {"running", "failed"} else "working"
        self._render_card()

    def _render_card(self) -> None:
        text = Text(no_wrap=True, overflow="crop")
        text.append(f"{self.agent_id:02d} ", style="bold #4a4a4a")
        text.append(SHORT_ROLE.get(self.agent_id, self.role[:14]).upper(), style="bold #d4d4d4")
        status_style = {
            "idle": "#4a4a4a",
            "working": "#8a8a8a",
            "running": "#bdbdbd",
            "done": "#8a8a8a",
            "failed": "#f5f5f5",
            "warning": "#a3a3a3",
        }.get(self.status, "#6b6b6b")
        text.append("  ", style="")
        text.append(self.status, style=status_style)
        for index, turn in enumerate(self.turns, start=1):
            style = {
                "running": "#bdbdbd",
                "failed": "#f5f5f5",
                "warning": "#a3a3a3",
            }.get(turn["status"], "#6b6b6b")
            detail = f"{turn['kind']} {turn['detail']}".strip()
            if len(detail) > 19:
                detail = detail[:19]
            stamp = (turn.get("timestamp") or "")[:5]
            text.append(f"\n  ↳{index} {stamp} {detail}", style=style)
        self.update(text)


class AgentRail(Vertical):
    def __init__(self):
        super().__init__(id="agent-rail")
        self._cards: dict[int, AgentCard] = {}
        self._phase = "idle"
        self._title = Static("AGENTS", classes="rail-title")

    def compose(self) -> ComposeResult:
        yield self._title
        with VerticalScroll(id="agent-scroll"):
            for role in ROSTER:
                card = AgentCard(role.id, role.title)
                self._cards[role.id] = card
                yield card

    def on_mount(self) -> None:
        self.border_title = "Agents"

    def set_phase(self, phase: str, detail: str = "") -> None:
        self._phase = phase or "idle"
        label = f"AGENTS  ·  {self._phase}".strip()
        self._title.update(Text(label[:30], style="bold #8a8a8a", no_wrap=True, overflow="crop"))

    def set_status(self, agent_id: int, role: str, status: str, detail: str = "") -> None:
        card = self._cards.get(agent_id)
        if card is None:
            card = AgentCard(agent_id, role or f"Agent {agent_id}")
            self._cards[agent_id] = card
        card.set_status(status)
        if detail:
            card.add_action("status", detail, status)

    def add_action(
        self,
        agent_id: int,
        role: str,
        kind: str,
        detail: str,
        status: str = "running",
        timestamp: str = "",
    ) -> None:
        card = self._cards.get(agent_id)
        if card is None:
            card = AgentCard(agent_id, role or f"Agent {agent_id}")
            self._cards[agent_id] = card
        card.add_action(kind, detail, status, timestamp)

    def clear(self) -> None:
        for card in self._cards.values():
            card.turns.clear()
            card.status = "idle"
            card._render()
