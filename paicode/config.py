import os
import json
from datetime import datetime
from pathlib import Path
from . import ui

# Define the standard configuration path in the user's home directory
CONFIG_DIR = Path.home() / ".config" / "pai-code"
KEY_FILE = CONFIG_DIR / "credentials"              # legacy single-key file
KEYS_FILE = CONFIG_DIR / "credentials.json"        # new multi-key store

def _ensure_config_dir_exists():
    """Ensures the configuration directory exists with correct permissions."""
    os.makedirs(CONFIG_DIR, exist_ok=True)
    os.chmod(CONFIG_DIR, 0o700)

def _secure_path(path: Path):
    try:
        os.chmod(path, 0o600)
    except Exception:
        pass

def _load_store() -> dict:
    """Load the JSON store; migrate from legacy single-key if necessary."""
    _ensure_config_dir_exists()
    if not KEYS_FILE.exists():
        # Attempt migration from legacy single-key file
        data = {"keys": [], "rr_index": 0}
        if KEY_FILE.exists():
            try:
                single = KEY_FILE.read_text().strip()
                if single:
                    data["keys"].append({
                        "id": 1,
                        "label": "default",
                        "key": single,
                        "enabled": True,
                        "created_at": datetime.utcnow().isoformat() + "Z"
                    })
            except Exception:
                pass
        with open(KEYS_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        _secure_path(KEYS_FILE)
        return data
    try:
        with open(KEYS_FILE, 'r') as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError("Invalid credentials.json structure")
        data.setdefault("keys", [])
        data.setdefault("rr_index", 0)
        return data
    except Exception as e:
        ui.print_error(f"Failed to load credentials store: {e}")
        return {"keys": [], "rr_index": 0}

def _save_store(data: dict):
    try:
        with open(KEYS_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        _secure_path(KEYS_FILE)
    except Exception as e:
        ui.print_error(f"Failed to save credentials store: {e}")

# ----- Single-key compatibility API -----
def save_api_key(api_key: str):
    """Backwards compatible: store as a single key named 'default'."""
    data = _load_store()
    keys = data.get("keys", [])
    # Replace or insert id=1 default
    default = next((k for k in keys if k.get("id") == 1), None)
    if default:
        default.update({"key": api_key, "enabled": True, "label": "default"})
    else:
        keys.append({
            "id": 1,
            "label": "default",
            "key": api_key,
            "enabled": True,
            "created_at": datetime.utcnow().isoformat() + "Z"
        })
    data["keys"] = keys
    _save_store(data)
    ui.print_success(f"API Key saved (id=1) to: {KEYS_FILE}")

def get_api_key() -> str | None:
    """Backwards compatible getter: return first enabled key if exists."""
    data = _load_store()
    for k in data.get("keys", []):
        if k.get("enabled", True) and k.get("key"):
            return k.get("key")
    # Fallback to legacy file
    if KEY_FILE.exists():
        try:
            return KEY_FILE.read_text().strip()
        except Exception:
            return None
    return None

def show_api_key():
    """Displays the first enabled API key in a masked format."""
    key = get_api_key()
    if not key:
        ui.print_error("API Key is not set. Please use: pai config --set <YOUR_API_KEY>")
        return
    masked = f"{key[:5]}...{key[-4:]}"
    ui.print_info(f"Current API Key (first enabled): {masked}")

def remove_api_key():
    """Removes the legacy API key file (compat)."""
    if KEY_FILE.exists():
        try:
            os.remove(KEY_FILE)
            ui.print_success("Success: Legacy API Key file removed.")
        except Exception as e:
            ui.print_error(f"Error: Failed to remove legacy API key file: {e}")
    else:
        ui.print_warning("No legacy API key file found to remove.")

# ----- Multi-key management API -----
def list_api_keys() -> list[dict]:
    data = _load_store()
    return data.get("keys", [])

def add_api_key(new_key: str, label: str | None = None) -> int:
    data = _load_store()
    keys = data.get("keys", [])
    next_id = (max((k.get("id", 0) for k in keys), default=0) + 1) if keys else 1
    entry = {
        "id": next_id,
        "label": label or f"key-{next_id}",
        "key": new_key,
        "enabled": True,
        "created_at": datetime.utcnow().isoformat() + "Z"
    }
    keys.append(entry)
    data["keys"] = keys
    _save_store(data)
    ui.print_success(f"Added API key id={next_id} ({entry['label']}).")
    return next_id

def edit_api_key(key_id: int, new_key: str):
    data = _load_store()
    found = False
    for k in data.get("keys", []):
        if k.get("id") == key_id:
            k["key"] = new_key
            found = True
            break
    if not found:
        ui.print_error(f"API key id={key_id} not found.")
        return
    _save_store(data)
    ui.print_success(f"Updated API key id={key_id}.")

def rename_api_key(key_id: int, new_label: str):
    data = _load_store()
    for k in data.get("keys", []):
        if k.get("id") == key_id:
            k["label"] = new_label
            _save_store(data)
            ui.print_success(f"Renamed API key id={key_id} to '{new_label}'.")
            return
    ui.print_error(f"API key id={key_id} not found.")

def remove_api_key_by_id(key_id: int):
    data = _load_store()
    before = len(data.get("keys", []))
    data["keys"] = [k for k in data.get("keys", []) if k.get("id") != key_id]
    after = len(data["keys"])
    _save_store(data)
    if after < before:
        ui.print_success(f"Removed API key id={key_id}.")
    else:
        ui.print_warning(f"API key id={key_id} not found.")

def enable_api_key(key_id: int, enabled: bool = True):
    data = _load_store()
    for k in data.get("keys", []):
        if k.get("id") == key_id:
            k["enabled"] = enabled
            _save_store(data)
            ui.print_success(("Enabled" if enabled else "Disabled") + f" API key id={key_id}.")
            return
    ui.print_error(f"API key id={key_id} not found.")

def get_enabled_keys() -> list[dict]:
    data = _load_store()
    return [k for k in data.get("keys", []) if k.get("enabled", True) and k.get("key")]

def get_rr_index() -> int:
    data = _load_store()
    return int(data.get("rr_index", 0))

def set_rr_index(idx: int):
    data = _load_store()
    data["rr_index"] = int(max(0, idx))
    _save_store(data)