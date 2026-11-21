from paicode.tui.commands import SLASH_COMMANDS, filter_commands, parse_slash


def test_parse_slash_with_args():
    command = parse_slash("/model deepseek-v4-pro")
    assert command is not None
    assert command.name == "model"
    assert command.args == "deepseek-v4-pro"


def test_parse_slash_without_args():
    command = parse_slash("/help")
    assert command is not None
    assert command.name == "help"
    assert command.args == ""


def test_parse_rejects_plain_text():
    assert parse_slash("hello") is None
    assert parse_slash("/") is None
    assert parse_slash("") is None


def test_filter_commands_by_prefix():
    matches = filter_commands("mo")
    assert [spec.name for spec in matches] == ["model", "models"]
    assert [spec.name for spec in filter_commands("MO")] == ["model", "models"]


def test_filter_commands_empty_fragment_returns_catalog():
    assert filter_commands("") == SLASH_COMMANDS
    assert filter_commands("zzz") == []
