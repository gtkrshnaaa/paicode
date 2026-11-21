from dataclasses import dataclass


HELP_TEXT = """Paicode slash commands:
/connect [preset]  configure a provider, base URL, and API key
/key [value]       add an API key to the active provider
/baseurl [url]     set the active provider base URL
/provider [name]   list or switch providers
/models            fetch models from the active provider
/model [name]      choose a model
/rules             show loaded PAICODE.md files
/skills            list installed skills
/skill <name>      print a skill
/stats             token and file statistics
/limits            show step and context limits
/config            show redacted provider configuration
/init              create a project PAICODE.md
/refresh           reload rules, skills, and the file tree
/clear             clear chat and diff panes
/new               start a fresh session
/exit              quit Paicode

Examples:
/connect deepseek
/connect opencode https://opencode.ai/inference/openai/v1
/model deepseek-flash
/connect custom https://example.com/v1"""


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
