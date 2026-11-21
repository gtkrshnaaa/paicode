from dataclasses import dataclass


@dataclass(frozen=True)
class SlashCommandSpec:
    name: str
    usage: str
    description: str


SLASH_COMMANDS = [
    SlashCommandSpec("help", "/help", "show this command list"),
    SlashCommandSpec("connect", "/connect [preset]", "configure a provider and API key"),
    SlashCommandSpec("key", "/key [value]", "add an API key to the active provider"),
    SlashCommandSpec("baseurl", "/baseurl [url]", "set the active provider base URL"),
    SlashCommandSpec("provider", "/provider [name]", "list or switch providers"),
    SlashCommandSpec("model", "/model [name]", "choose a model"),
    SlashCommandSpec("models", "/models", "fetch models from the active provider"),
    SlashCommandSpec("rules", "/rules", "show loaded PAICODE.md files"),
    SlashCommandSpec("skills", "/skills", "list installed skills"),
    SlashCommandSpec("skill", "/skill <name>", "print a skill"),
    SlashCommandSpec("stats", "/stats", "token and file statistics"),
    SlashCommandSpec("limits", "/limits", "show step and context limits"),
    SlashCommandSpec("config", "/config", "show redacted provider configuration"),
    SlashCommandSpec("init", "/init", "create a project PAICODE.md"),
    SlashCommandSpec("refresh", "/refresh", "reload rules, skills, and files"),
    SlashCommandSpec("clear", "/clear", "clear chat and diff panes"),
    SlashCommandSpec("new", "/new", "start a fresh session"),
    SlashCommandSpec("exit", "/exit", "quit Paicode"),
]

HELP_TEXT = "\n".join(
    ["Paicode slash commands:"]
    + [f"{spec.usage:<22} {spec.description}" for spec in SLASH_COMMANDS]
    + [
        "",
        "Examples:",
        "/connect deepseek",
        "/connect opencode https://opencode.ai/inference/openai/v1",
        "/model deepseek-flash",
        "/connect custom https://example.com/v1",
    ]
)


@dataclass
class SlashCommand:
    name: str
    args: str
    raw: str


def parse_slash(text: str) -> SlashCommand | None:
    stripped = text.strip()
    if not stripped.startswith("/"):
        return None
    body = stripped[1:].strip()
    if not body:
        return None
    parts = body.split(maxsplit=1)
    return SlashCommand(
        name=parts[0].lower(),
        args=parts[1].strip() if len(parts) > 1 else "",
        raw=stripped,
    )


def filter_commands(fragment: str) -> list[SlashCommandSpec]:
    needle = fragment.strip().lower()
    if not needle:
        return list(SLASH_COMMANDS)
    return [spec for spec in SLASH_COMMANDS if spec.name.startswith(needle)]
