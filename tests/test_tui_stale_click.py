from pathlib import Path

import pytest
from textual import events
from textual.geometry import Offset
from textual.widgets import Static

from paicode.providers.store import ProviderStore
from paicode.tui.app import PaiCodeApp
from paicode.tui.screen import PaiCodeScreen


def mouse_down() -> events.MouseDown:
    return events.MouseDown(None, 1, 1, 0, 0, 1, False, False, False)


async def test_default_screen_is_guarded(project: Path, config_home: Path):
    app = PaiCodeApp(project, ProviderStore())
    async with app.run_test(size=(160, 50)) as pilot:
        await pilot.pause()
        assert isinstance(app.screen, PaiCodeScreen)


async def test_detached_markdown_cell_click_is_ignored(
    project: Path, config_home: Path
):
    app = PaiCodeApp(project, ProviderStore())
    async with app.run_test(size=(160, 50)) as pilot:
        await pilot.pause()
        screen = app.screen
        detached = Static("stale markdown cell")
        original = screen.get_widget_and_offset_at
        screen.get_widget_and_offset_at = lambda x, y: (detached, Offset(0, 0))
        try:
            screen._forward_event(mouse_down())
        finally:
            screen.get_widget_and_offset_at = original
        assert screen._select_state is None


async def test_mounted_widget_click_still_starts_selection(
    project: Path, config_home: Path
):
    app = PaiCodeApp(project, ProviderStore())
    async with app.run_test(size=(160, 50)) as pilot:
        await pilot.pause()
        screen = app.screen
        mounted = app.query_one("#topbar", Static)
        original = screen.get_widget_and_offset_at
        screen.get_widget_and_offset_at = lambda x, y: (mounted, Offset(0, 0))
        try:
            screen._forward_event(mouse_down())
        finally:
            screen.get_widget_and_offset_at = original
        assert screen._select_state is not None


async def test_unrelated_attribute_error_propagates(
    project: Path, config_home: Path
):
    app = PaiCodeApp(project, ProviderStore())
    async with app.run_test(size=(160, 50)) as pilot:
        await pilot.pause()
        screen = app.screen
        original = screen.get_widget_and_offset_at

        def boom(x, y):
            raise AttributeError("unrelated failure")

        screen.get_widget_and_offset_at = boom
        try:
            with pytest.raises(AttributeError, match="unrelated failure"):
                screen._forward_event(mouse_down())
        finally:
            screen.get_widget_and_offset_at = original
