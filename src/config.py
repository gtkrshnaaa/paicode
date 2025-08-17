import os
from pathlib import Path
from . import ui

# Define the standard configuration path in the user's home directory
CONFIG_DIR = Path.home() / ".config" / "pai-code"
KEY_FILE = CONFIG_DIR / "credentials"

def _ensure_config_dir_exists():
    """Ensures the configuration directory exists with correct permissions."""
    os.makedirs(CONFIG_DIR, exist_ok=True)
    os.chmod(CONFIG_DIR, 0o700) 

def save_api_key(api_key: str):
    """Saves the API key to a file with secure permissions."""
    try:
        _ensure_config_dir_exists()
        with open(KEY_FILE, 'w') as f:
            f.write(api_key)
        # Set file permissions to be readable/writable only by the owner
        os.chmod(KEY_FILE, 0o600)
        ui.print_success(f"API Key has been saved to: {KEY_FILE}")
    except Exception as e:
        ui.print_error(f"Failed to save API key: {e}")

def get_api_key() -> str | None:
    """Reads the API key from the configuration file."""
    if not KEY_FILE.exists():
        return None
    try:
        # Check permissions before reading for added security
        if os.stat(KEY_FILE).st_mode & 0o077:
            ui.print_warning(f"API key file at {KEY_FILE} has insecure permissions. Recommended: 600.")
        
        return KEY_FILE.read_text().strip()
    except Exception as e:
        ui.print_error(f"Failed to read API key: {e}")
        return None

def show_api_key():
    """Displays the stored API key in a masked format."""
    api_key = get_api_key()
    if not api_key:
        ui.print_error("API Key is not set. Please use: pai config --set <YOUR_API_KEY>")
        return
        
    # Mask the middle of the key for security
    masked_key = f"{api_key[:5]}...{api_key[-4:]}"
    ui.print_info(f"Current API Key: {masked_key}")

def remove_api_key():
    """Removes the API key file."""
    if KEY_FILE.exists():
        try:
            os.remove(KEY_FILE)
            ui.print_success("Success: API Key has been removed.")
        except Exception as e:
            ui.print_error(f"Error: Failed to remove API key: {e}")
    else:
        ui.print_warning("No stored API key found to remove.")