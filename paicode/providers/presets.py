from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderPreset:
    name: str
    base_url: str
    model: str
    models_url: str = ""


PRESETS: dict[str, ProviderPreset] = {
    "deepseek": ProviderPreset(
        name="deepseek",
        base_url="https://api.deepseek.com/v1",
        model="deepseek-flash",
    ),
    "opencode": ProviderPreset(
        name="opencode",
        base_url="https://opencode.ai/inference/openai/v1",
        model="deepseek-v4.1-flash",
        models_url="https://opencode.ai/inference/v1/models",
    ),
    "openai": ProviderPreset(
        name="openai",
        base_url="https://api.openai.com/v1",
        model="gpt-5.1",
    ),
    "openrouter": ProviderPreset(
        name="openrouter",
        base_url="https://openrouter.ai/api/v1",
        model="",
    ),
    "google": ProviderPreset(
        name="google",
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        model="gemini-3.5-flash",
    ),
    "custom": ProviderPreset(
        name="custom",
        base_url="",
        model="",
    ),
}


def get_preset(name: str) -> ProviderPreset | None:
    return PRESETS.get(name.strip().lower())


def preset_summary() -> str:
    lines = []
    for key, preset in PRESETS.items():
        if preset.base_url:
            lines.append(f"{key}: {preset.base_url}")
    return "\n".join(lines)
