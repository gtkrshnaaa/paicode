import os
import shutil
import subprocess

IMAGE_TYPES = ("image/png", "image/jpeg", "image/webp")


def _run(command: list[str]) -> bytes:
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return b""
    return result.stdout if result.returncode == 0 else b""


def read_clipboard_text() -> str:
    if shutil.which("wl-paste"):
        data = _run(["wl-paste", "--no-newline"])
        if data:
            return data.decode("utf-8", errors="ignore")
    if shutil.which("xclip") and os.getenv("DISPLAY"):
        data = _run(["xclip", "-selection", "clipboard", "-o"])
        if data:
            return data.decode("utf-8", errors="ignore")
    return ""


def read_clipboard_image() -> tuple[str, bytes] | None:
    if shutil.which("wl-paste"):
        types = _run(["wl-paste", "--list-types"]).decode("utf-8", errors="ignore")
        for mime in IMAGE_TYPES:
            if mime in types:
                data = _run(["wl-paste", "--type", mime])
                if data:
                    return mime, data

    if shutil.which("xclip") and os.getenv("DISPLAY"):
        targets = _run(
            ["xclip", "-selection", "clipboard", "-t", "TARGETS", "-o"]
        ).decode("utf-8", errors="ignore")
        for mime in IMAGE_TYPES:
            if mime in targets:
                data = _run(["xclip", "-selection", "clipboard", "-t", mime, "-o"])
                if data:
                    return mime, data
    return None
