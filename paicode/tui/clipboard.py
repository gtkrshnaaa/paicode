import os
import shutil
import subprocess

IMAGE_TYPES = ("image/png", "image/jpeg", "image/webp")
TEXT_TYPES = ("text/plain;charset=utf-8", "text/plain", "UTF8_STRING")


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
        for mime in TEXT_TYPES:
            data = _run(["wl-paste", "--no-newline", "--type", mime])
            if data:
                return data.decode("utf-8", errors="ignore")
    if shutil.which("xclip") and os.getenv("DISPLAY"):
        for mime in TEXT_TYPES:
            data = _run(["xclip", "-selection", "clipboard", "-t", mime, "-o"])
            if data:
                return data.decode("utf-8", errors="ignore")
    return ""


def write_clipboard_text(text: str) -> bool:
    if not text:
        return False
    data = text.encode("utf-8")
    if shutil.which("wl-copy"):
        if _write(["wl-copy", "--type", "text/plain;charset=utf-8"], data):
            return True
    if shutil.which("xclip") and os.getenv("DISPLAY"):
        if _write(["xclip", "-selection", "clipboard"], data):
            return True
    return False


def _write(command: list[str], data: bytes) -> bool:
    try:
        result = subprocess.run(
            command,
            input=data,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0


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
