import os
from pathlib import Path
import json
from typing import Optional
from . import ui

# Define the standard configuration path in the user's home directory
CONFIG_DIR = Path.home() / ".config" / "pai-code"
KEY_FILE = CONFIG_DIR / "credentials.json"

def _ensure_config_dir_exists():
    """Ensures the configuration directory exists with correct permissions."""
    os.makedirs(CONFIG_DIR, exist_ok=True)
    os.chmod(CONFIG_DIR, 0o700)

def _default_config() -> dict:
    """Default single-key configuration."""
    return {
        "version": 2,  # Version 2 = single-key system
        "api_key": None
    }

def _load_config() -> dict:
    """Load the single-key configuration."""
    _ensure_config_dir_exists()
    if not KEY_FILE.exists():
        return _default_config()
    
    try:
        with open(KEY_FILE, 'r') as f:
            data = json.load(f)
        
        # Migrate from old multi-key system if needed
        if data.get("version") == 1 and "keys" in data:
            # Old multi-key system - migrate to single key
            old_keys = data.get("keys", {})
            default_id = data.get("default")
            
            if default_id and default_id in old_keys:
                migrated_key = old_keys[default_id]
                ui.print_info(f"Migrating from multi-key system. Using key '{default_id}' as single key.")
                return {"version": 2, "api_key": migrated_key}
            elif old_keys:
                # Use first available key
                first_key = list(old_keys.values())[0]
                ui.print_info("Migrating from multi-key system. Using first available key.")
                return {"version": 2, "api_key": first_key}
        
        # Ensure proper structure
        if not isinstance(data, dict):
            return _default_config()
        
        return data
        
    except (json.JSONDecodeError, IOError):
        ui.print_warning("Configuration file corrupted. Creating new one.")
        return _default_config()

def _save_config(config: dict) -> None:
    """Save the single-key configuration."""
    try:
        _ensure_config_dir_exists()
        with open(KEY_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        os.chmod(KEY_FILE, 0o600)
    except Exception as e:
        ui.print_error(f"Failed to save configuration: {e}")

def set_api_key(api_key: str) -> None:
    """Set the API key."""
    if not api_key or not isinstance(api_key, str):
        ui.print_error("Invalid API key provided.")
        return
    
    if not api_key.startswith("AIza"):
        ui.print_warning("Warning: API key doesn't look like a Google API key (should start with 'AIza')")
    
    config = _load_config()
    config["api_key"] = api_key
    _save_config(config)
    
    masked_key = mask_api_key(api_key)
    ui.print_success(f"✓ API key set successfully: {masked_key}")

def get_api_key() -> Optional[str]:
    """Get the current API key."""
    config = _load_config()
    return config.get("api_key")

def save_api_key(api_key: str):
    """Legacy compatibility function."""
    set_api_key(api_key)

def remove_api_key() -> None:
    """Remove the stored API key."""
    config = _load_config()
    
    if not config.get("api_key"):
        ui.print_info("No API key is currently set.")
        return
    
    config["api_key"] = None
    _save_config(config)
    ui.print_success("✓ API key removed successfully.")

def show_api_key() -> None:
    """Show the current API key (masked)."""
    api_key = get_api_key()
    
    if not api_key:
        ui.print_info("No API key is currently set.")
        ui.print_info("Use 'pai config set <API_KEY>' to set one.")
        return
    
    masked_key = mask_api_key(api_key)
    ui.print_info(f"Current API key: {masked_key}")

def mask_api_key(api_key: str) -> str:
    """Mask API key for display purposes."""
    if not api_key or len(api_key) < 10:
        return "***"
    
    return f"{api_key[:6]}...{api_key[-4:]}"

def is_configured() -> bool:
    """Check if API key is configured."""
    api_key = get_api_key()
    return api_key is not None and len(api_key.strip()) > 0

def validate_api_key() -> tuple[bool, str]:
    """Validate that API key is configured and looks correct."""
    api_key = get_api_key()
    
    if not api_key:
        return False, "No API key configured. Use 'pai config set <API_KEY>' to set one."
    
    if not api_key.startswith("AIza"):
        return False, "API key doesn't look like a Google API key (should start with 'AIza')"
    
    if len(api_key) < 20:
        return False, "API key seems too short to be valid"
    
    return True, "API key looks valid"

# Legacy compatibility functions (simplified)
def add_api_key(key_id: str, api_key: str) -> None:
    """Legacy function - redirect to set_api_key."""
    ui.print_info(f"Note: Multi-key system deprecated. Setting '{key_id}' as single API key.")
    set_api_key(api_key)

def list_api_keys() -> list:
    """Legacy function - return single key info."""
    api_key = get_api_key()
    if not api_key:
        return []
    
    return [{
        "id": "single",
        "masked": mask_api_key(api_key),
        "is_default": "yes"
    }]

def set_default_api_key(key_id: str) -> None:
    """Legacy function - no-op in single-key system."""
    ui.print_info("Note: Default key setting not needed in single-key system.")

def load_api_key() -> Optional[str]:
    """Legacy function - redirect to get_api_key."""
    return get_api_key()

def is_configured() -> bool:
    """Check if API key is configured."""
    api_key = get_api_key()
    return api_key is not None and len(api_key.strip()) > 0

def validate_api_key() -> tuple[bool, str]:
    """Validate the current API key."""
    api_key = get_api_key()
    
    if not api_key:
        return False, "No API key configured. Use 'pai config set <API_KEY>' to set one."
    
    if not api_key.startswith("AIza"):
        return False, "API key doesn't look like a Google API key (should start with 'AIza')"
    
    if len(api_key) < 30:
        return False, "API key seems too short to be valid"
    
    return True, "API key looks valid"

def show_api_key():
    """Show the current API key (masked)."""
    api_key = get_api_key()
    
    if not api_key:
        ui.print_info("No API key is currently configured.")
        ui.print_info("Use 'pai config set <API_KEY>' to set your Google Gemini API key.")
        return
    
    masked_key = mask_api_key(api_key)
    ui.print_info(f"Current API key: {masked_key}")