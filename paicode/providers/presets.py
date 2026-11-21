from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderPreset:
    name: str
    base_url: str
    model: str = ""
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
    ),
    "openrouter": ProviderPreset(
        name="openrouter",
        base_url="https://openrouter.ai/api/v1",
    ),
    "google": ProviderPreset(
        name="google",
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    ),
    "groq": ProviderPreset(
        name="groq",
        base_url="https://api.groq.com/openai/v1",
    ),
    "mistral": ProviderPreset(
        name="mistral",
        base_url="https://api.mistral.ai/v1",
    ),
    "xai": ProviderPreset(
        name="xai",
        base_url="https://api.x.ai/v1",
    ),
    "together": ProviderPreset(
        name="together",
        base_url="https://api.together.xyz/v1",
    ),
    "fireworks": ProviderPreset(
        name="fireworks",
        base_url="https://api.fireworks.ai/inference/v1",
    ),
    "perplexity": ProviderPreset(
        name="perplexity",
        base_url="https://api.perplexity.ai",
    ),
    "cerebras": ProviderPreset(
        name="cerebras",
        base_url="https://api.cerebras.ai/v1",
    ),
    "sambanova": ProviderPreset(
        name="sambanova",
        base_url="https://api.sambanova.ai/v1",
    ),
    "moonshot": ProviderPreset(
        name="moonshot",
        base_url="https://api.moonshot.ai/v1",
    ),
    "zhipu": ProviderPreset(
        name="zhipu",
        base_url="https://open.bigmodel.cn/api/paas/v4",
    ),
    "dashscope": ProviderPreset(
        name="dashscope",
        base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
    ),
    "minimax": ProviderPreset(
        name="minimax",
        base_url="https://api.minimax.io/v1",
    ),
    "nvidia": ProviderPreset(
        name="nvidia",
        base_url="https://integrate.api.nvidia.com/v1",
    ),
    "hyperbolic": ProviderPreset(
        name="hyperbolic",
        base_url="https://api.hyperbolic.xyz/v1",
    ),
    "novita": ProviderPreset(
        name="novita",
        base_url="https://api.novita.ai/v3/openai",
    ),
    "deepinfra": ProviderPreset(
        name="deepinfra",
        base_url="https://api.deepinfra.com/v1/openai",
    ),
    "github": ProviderPreset(
        name="github",
        base_url="https://models.github.ai/inference",
    ),
    "ollama": ProviderPreset(
        name="ollama",
        base_url="http://localhost:11434/v1",
    ),
    "lmstudio": ProviderPreset(
        name="lmstudio",
        base_url="http://localhost:1234/v1",
    ),
    "custom": ProviderPreset(
        name="custom",
        base_url="",
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
