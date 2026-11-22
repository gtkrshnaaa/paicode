import json
from pathlib import Path

import pytest

from paicode.core.errors import ConfigError
from paicode.settings import (
    Budget,
    load_settings,
    permission_effect,
)


def write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_project_settings_override_global(project: Path, config_home: Path):
    write(
        config_home / "settings.json",
        {
            "permission_mode": "standard",
            "budget": {"max_tokens": 1000, "prompt_price_per_million": 1.0},
            "mcp": {"servers": {"docs": {"transport": "http", "url": "http://127.0.0.1:9/mcp"}}},
        },
    )
    write(
        project / ".paicode" / "settings.json",
        {
            "permission_mode": "strict",
            "budget": {"max_tokens": 250},
            "hooks": [{"event": "pre_tool", "command": "true"}],
            "plugins": ["example.py"],
        },
    )
    settings = load_settings(project)
    assert settings.permission_mode == "strict"
    assert settings.budget.max_tokens == 250
    assert settings.budget.prompt_price_per_million == 1.0
    assert settings.mcp_servers["docs"].transport == "http"
    assert settings.hooks[0].event == "pre_tool"
    assert settings.plugins == ["example.py"]


def test_permission_rule_last_match_wins(project: Path, config_home: Path):
    write(
        project / ".paicode" / "settings.json",
        {
            "permissions": [
                {"action": "shell", "resource": "*", "effect": "deny"},
                {"action": "shell", "resource": "git status*", "effect": "allow"},
                {"action": "shell", "resource": "rm *", "effect": "deny"},
            ]
        },
    )
    settings = load_settings(project)
    assert permission_effect(settings, "shell", "git status --short") == "allow"
    assert permission_effect(settings, "shell", "rm -rf build") == "deny"
    assert permission_effect(settings, "shell", "npm test") == "deny"


def test_strict_mode_turns_defaults_into_ask(project: Path, config_home: Path):
    write(project / ".paicode" / "settings.json", {"permission_mode": "strict"})
    settings = load_settings(project)
    assert permission_effect(settings, "shell", "pytest -q") == "ask"
    assert permission_effect(settings, "read", "README.md") == "allow"


def test_budget_cost_and_exceeded():
    budget = Budget(max_tokens=100, max_cost_usd=0.01, prompt_price_per_million=2.0, completion_price_per_million=4.0)
    assert budget.cost(1_000, 500) == pytest.approx(0.004)
    assert budget.exceeded(101, 0.0).startswith("Token budget exceeded")
    assert budget.exceeded(1, 0.02).startswith("Cost budget exceeded")
    assert budget.exceeded(1, 0.001) == ""


def test_invalid_permission_effect_is_rejected(project: Path, config_home: Path):
    write(
        project / ".paicode" / "settings.json",
        {"permissions": [{"action": "shell", "resource": "*", "effect": "maybe"}]},
    )
    with pytest.raises(ConfigError):
        load_settings(project)


def test_cache_aware_cost():
    budget = Budget(
        prompt_price_per_million=0.15,
        cache_hit_price_per_million=0.003,
        completion_price_per_million=0.60,
    )
    cost = budget.cost_detailed(1_000_000, 1_000_000, 960_000, 40_000)
    assert cost == pytest.approx(0.003 * 0.96 + 0.15 * 0.04 + 0.60)
