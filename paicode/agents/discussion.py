from pathlib import Path

from ..agent.loop import AgentRunner
from ..agent.prompts import build_system_prompt
from ..core.stats import UsageStats
from ..providers.store import ProviderConfig

DISCUSSION_PROMPT = """

DISCUSSION MODE IS ACTIVE.
You are a read-only architecture discussion partner.
- Do not create, edit, delete, move, format, or generate project files.
- Do not call write, edit, mkdir, move, delete, or any mutating tool.
- Do not run builds, package installs, git mutations, or shell redirection.
- Use read, list, glob, grep, explore, and read-only bash inspection only.
- Analyze the codebase, compare options, explain tradeoffs, and recommend a plan.
- Code snippets in chat are allowed only as explanation and must not be written to disk.
- Finish with a concise discussion summary and recommended next action.
"""


class DiscussionRunner:
    def __init__(self, root: Path, provider: ProviderConfig, stats: UsageStats, rules, skills, emit):
        self.root = root
        self.provider = provider
        self.stats = stats
        self.rules = rules
        self.skills = skills
        self.emit = emit
        self._runner: AgentRunner | None = None

    def request_stop(self) -> None:
        if self._runner is not None:
            self._runner.request_stop()

    def run(self, user_text: str, images=None) -> str:
        prompt = build_system_prompt(self.root, self.rules, self.skills) + DISCUSSION_PROMPT
        self._runner = AgentRunner(
            self.root,
            self.provider,
            self.stats,
            self.rules,
            self.skills,
            emit=self.emit,
            system_prompt=prompt,
            allowed_write_paths=set(),
            read_only_shell=True,
            strict_read_only_shell=True,
        )
        return self._runner.run(user_text, images=images)
