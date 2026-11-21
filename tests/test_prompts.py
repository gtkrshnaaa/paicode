from pathlib import Path

from paicode.agent.prompts import build_system_prompt


def test_prompt_states_workspace_and_exploration_policy(project: Path):
    prompt = build_system_prompt(project, [], [])
    assert str(project) in prompt
    assert "Current working directory" in prompt
    assert "Home directory" in prompt
    assert "OS exploration policy" in prompt
    assert "explore" in prompt
    assert "Never write, edit, delete, or move outside the project root" in prompt
