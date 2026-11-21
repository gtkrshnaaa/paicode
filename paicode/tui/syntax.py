from pathlib import Path

from pygments import lex
from pygments.lexers import get_lexer_by_name
from pygments.token import Comment, Keyword, Literal, Name, Number, Operator, Token
from rich.style import Style
from rich.text import Text

LANGUAGES = {
    ".py": "python",
    ".js": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".json": "json",
    ".md": "markdown",
    ".sh": "bash",
    ".bash": "bash",
    ".zsh": "bash",
    ".css": "css",
    ".scss": "css",
    ".html": "html",
    ".htm": "html",
    ".vue": "html",
    ".svelte": "html",
    ".xml": "xml",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".rs": "rust",
    ".go": "go",
    ".java": "java",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".hpp": "cpp",
    ".sql": "sql",
    ".ini": "ini",
    ".conf": "ini",
    ".rb": "ruby",
    ".php": "php",
    ".swift": "swift",
    ".kt": "kotlin",
    ".kts": "kotlin",
    ".cs": "csharp",
    ".lua": "lua",
    ".r": "r",
    ".pl": "perl",
}
SPECIAL_NAMES = {
    "dockerfile": "docker",
    "makefile": "make",
    ".env": "bash",
}
TOKEN_STYLES = (
    (Token.Comment, Style(color="#5a5a5a", italic=True)),
    (Token.Keyword, Style(color="#ffffff", bold=True)),
    (Name.Function, Style(color="#ededed", bold=True)),
    (Name.Class, Style(color="#ffffff", bold=True)),
    (Name.Tag, Style(color="#ededed")),
    (Name.Builtin, Style(color="#d4d4d4")),
    (Literal.String, Style(color="#a8a8a8", italic=True)),
    (Literal.Number, Style(color="#c0c0c0")),
    (Number, Style(color="#c0c0c0")),
    (Operator, Style(color="#9a9a9a")),
)
DEFAULT_STYLE = Style(color="#c8c8c8")
_LEXERS: dict[str, object] = {}


def language_for_path(path: Path | str) -> str | None:
    value = Path(path)
    if value.name.lower() in SPECIAL_NAMES:
        return SPECIAL_NAMES[value.name.lower()]
    return LANGUAGES.get(value.suffix.lower())


def _lexer(language: str | None):
    if not language:
        return None
    if language in _LEXERS:
        return _LEXERS[language]
    try:
        lexer = get_lexer_by_name(language, stripnl=False, ensurenl=False)
    except Exception:
        lexer = None
    _LEXERS[language] = lexer
    return lexer


def _style(token_type, background: str | None) -> Style:
    for needle, style in TOKEN_STYLES:
        if token_type in needle:
            return Style(color=style.color, bold=style.bold, italic=style.italic, bgcolor=background)
    return Style(color=DEFAULT_STYLE.color, bgcolor=background)


def highlight_code(code: str, language: str | None, background: str | None = None) -> Text:
    text = Text(no_wrap=True, overflow="crop")
    lexer = _lexer(language)
    if lexer is None:
        text.append(code, style=Style(color=DEFAULT_STYLE.color, bgcolor=background))
        return text
    try:
        tokens = list(lex(code, lexer))
    except Exception:
        text.append(code, style=Style(color=DEFAULT_STYLE.color, bgcolor=background))
        return text
    for token_type, value in tokens:
        if value:
            text.append(value, style=_style(token_type, background))
    return text


def highlight_diff_line(path: str, line: str) -> Text:
    if line.startswith("+++") or line.startswith("---"):
        return Text(line, no_wrap=True, overflow="crop", style="bold #6b6b6b")
    if line.startswith("@@"):
        return Text(line, no_wrap=True, overflow="crop", style="bold #bdbdbd")
    marker = line[:1] if line[:1] in {"+", "-", " "} else ""
    code = line[1:] if marker else line
    background = "#121212" if marker == "+" else "#0e0e0e" if marker == "-" else None
    text = Text(no_wrap=True, overflow="crop")
    if marker:
        marker_style = "#f5f5f5 bold" if marker == "+" else "#8a8a8a" if marker == "-" else "#707070"
        text.append(marker, style=Style.parse(marker_style) + Style(bgcolor=background))
    text.append_text(highlight_code(code, language_for_path(path), background))
    return text
