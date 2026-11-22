import threading
from typing import Callable

ApprovalHandler = Callable[[str, str], bool]

_HANDLER: ApprovalHandler | None = None
_LOCK = threading.Lock()


def set_approval_handler(handler: ApprovalHandler | None) -> None:
    global _HANDLER
    with _LOCK:
        _HANDLER = handler


def request_approval(action: str, resource: str) -> bool:
    with _LOCK:
        handler = _HANDLER
    if handler is None:
        return False
    try:
        return bool(handler(action, resource))
    except Exception:
        return False
