import os
from pathlib import Path
import json
from typing import Optional, Tuple, Dict, Any, List
from . import ui

# Define the standard configuration path in the user's home directory
CONFIG_DIR = Path.home() / ".config" / "pai-code"
KEY_FILE = CONFIG_DIR / "credentials"

def _ensure_config_dir_exists():
    """Ensures the configuration directory exists with correct permissions."""
    os.makedirs(CONFIG_DIR, exist_ok=True)
    os.chmod(CONFIG_DIR, 0o700)

def _default_store() -> Dict[str, Any]:
    return {
        "version": 1,
        "default": None,  # key id
        "keys": {},       # {id: api_key}
        "rr_index": 0,    # round-robin cursor
        "order": []       # stable order of ids for round-robin
    }

def _load_store() -> Dict[str, Any]:
    """Load the multi-key JSON store. If legacy plaintext is found, migrate it."""
    _ensure_config_dir_exists()
    if not KEY_FILE.exists():
        return _default_store()
    try:
        raw = KEY_FILE.read_text().strip()
        try:
            data = json.loads(raw)
            # basic shape validation
            if not isinstance(data, dict) or "keys" not in data:
                raise ValueError("Invalid credentials store format")
            # normalize order
            if "order" not in data or not isinstance(data.get("order"), list):
                data["order"] = list(data.get("keys", {}).keys())
            if "rr_index" not in data or not isinstance(data.get("rr_index"), int):
                data["rr_index"] = 0
            if "version" not in data:
                data["version"] = 1
            return data
        except json.JSONDecodeError:
            # Legacy plaintext: single key. Migrate.
            key = raw
            store = _default_store()
            store["keys"]["primary"] = key
            store["default"] = "primary"
            store["order"] = ["primary"]
            _save_store(store)
            ui.print_info("Migrated legacy single API key to multi-key store as id 'primary'.")
            return store
    except Exception as e:
        ui.print_error(f"Failed to read credentials: {e}")
        return _default_store()

def _save_store(data: Dict[str, Any]) -> None:
    try:
        _ensure_config_dir_exists()
        with open(KEY_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        os.chmod(KEY_FILE, 0o600)
    except Exception as e:
        ui.print_error(f"Failed to save credentials: {e}")

def save_api_key(api_key: str):
    """Backward-compatible: save a single API key as the default under id 'primary'."""
    add_api_key("primary", api_key)
    set_default_api_key("primary")

def get_api_key() -> Optional[str]:
    """Return the default API key (value) if set."""
    store = _load_store()
    default_id = store.get("default")
    if not default_id:
        return None
    return store.get("keys", {}).get(default_id)

def get_default_key_id() -> Optional[str]:
    store = _load_store()
    return store.get("default")

def add_api_key(key_id: str, api_key: str) -> None:
    if not key_id or any(ch in key_id for ch in (' ', '\t', '\n')):
        ui.print_error("Error: key id must be a simple identifier without spaces.")
        return
    store = _load_store()
    created = key_id not in store["keys"]
    store["keys"][key_id] = api_key
    if created:
        store["order"].append(key_id)
    if not store.get("default"):
        store["default"] = key_id
    _save_store(store)
    ui.print_success(f"API key '{key_id}' has been {'added' if created else 'updated'}.")

def list_api_keys() -> List[Dict[str, str]]:
    """Return a list of keys with id and masked value for display."""
    store = _load_store()
    rows = []
    default_id = store.get("default")
    for kid in store.get("order", []):
        val = store["keys"].get(kid, "")
        if val:
            # Handle short keys gracefully
            if len(val) < 10:
                masked = f"{val[:2]}...{val[-2:]}"
            else:
                masked = f"{val[:5]}...{val[-4:]}"
        else:
            masked = ""
        rows.append({
            "id": kid,
            "masked": masked,
            "is_default": "yes" if kid == default_id else ""
        })
    return rows

def show_api_key(key_id: Optional[str] = None):
    """Displays a masked API key. If key_id is None, show default."""
    store = _load_store()
    if key_id is None:
        key_id = store.get("default")
        if not key_id:
            ui.print_error("API Key is not set. Please add one: pai config add <ID> <API_KEY>")
            return
    val = store.get("keys", {}).get(key_id)
    if not val:
        ui.print_error(f"API key id '{key_id}' not found.")
        return
    # Handle short keys gracefully
    if len(val) < 10:
        masked_key = f"{val[:2]}...{val[-2:]}"
    else:
        masked_key = f"{val[:5]}...{val[-4:]}"
    suffix = " (default)" if key_id == store.get("default") else ""
    ui.print_info(f"Key [{key_id}]{suffix}: {masked_key}")

def remove_api_key(key_id: str) -> None:
    store = _load_store()
    if key_id not in store.get("keys", {}):
        ui.print_warning(f"No API key found with id '{key_id}'.")
        return
    # Remove
    del store["keys"][key_id]
    if key_id in store.get("order", []):
        store["order"].remove(key_id)
    # Adjust default if needed
    if store.get("default") == key_id:
        store["default"] = store["order"][0] if store.get("order") else None
    # Reset rr_index if out of bounds
    if store.get("rr_index", 0) >= len(store.get("order", [])):
        store["rr_index"] = 0
    _save_store(store)
    ui.print_success(f"Removed API key '{key_id}'.")

def set_default_api_key(key_id: str) -> None:
    store = _load_store()
    if key_id not in store.get("keys", {}):
        ui.print_error(f"API key id '{key_id}' not found.")
        return
    store["default"] = key_id
    _save_store(store)
    ui.print_success(f"Default API key set to '{key_id}'.")

def next_api_key() -> Optional[Tuple[str, str]]:
    """Round-robin over available keys. Returns (key_id, key_value)."""
    store = _load_store()
    order = store.get("order", [])
    if not order:
        return None
    idx = store.get("rr_index", 0) % len(order)
    key_id = order[idx]
    key_val = store.get("keys", {}).get(key_id)
    # advance cursor
    store["rr_index"] = (idx + 1) % len(order)
    _save_store(store)
    return (key_id, key_val)