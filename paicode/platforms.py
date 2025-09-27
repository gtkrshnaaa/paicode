import platform
from dataclasses import dataclass

@dataclass
class OsInfo:
    name: str           # linux | windows | darwin
    shell: str          # bash | powershell | sh
    path_sep: str       # '/' or '\\'


def detect_os() -> OsInfo:
    sys = platform.system().lower()
    if 'windows' in sys:
        return OsInfo(name='windows', shell='powershell', path_sep='\\')
    elif 'darwin' in sys:
        return OsInfo(name='darwin', shell='bash', path_sep='/')
    else:
        # default to linux-like
        return OsInfo(name='linux', shell='bash', path_sep='/')
