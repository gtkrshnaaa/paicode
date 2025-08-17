# pai_code/config.py

import os
from pathlib import Path

# Define the standard configuration path in the user's home directory
CONFIG_DIR = Path.home() / ".config" / "pai-code"
KEY_FILE = CONFIG_DIR / "credentials"

def _ensure_config_dir_exists():
    """Ensure the configuration directory exists."""
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
        print(f"Success: API Key has been saved to: {KEY_FILE}")
    except Exception as e:
        print(f"Error: Failed to save API key: {e}")

def get_api_key() -> str | None:
    """Reads the API key from the configuration file."""
    if not KEY_FILE.exists():
        return None
    try:
        # Check permissions before reading for added security
        if os.stat(KEY_FILE).st_mode & 0o077:
             print(f"Warning: API key file at {KEY_FILE} has insecure permissions. It is recommended to set them to 600.")
        
        return KEY_FILE.read_text().strip()
    except Exception as e:
        print(f"Error: Failed to read API key: {e}")
        return None

def show_api_key():
    """Displays the stored API key in a masked format."""
    api_key = get_api_key()
    if not api_key:
        print("API Key is not set. Please use the command:\npai config --set <YOUR_API_KEY>")
        return
        
    # Mask the middle of the key for security
    masked_key = f"{api_key[:5]}...{api_key[-4:]}"
    print(f"Current API Key: {masked_key}")

def remove_api_key():
    """Removes the API key file."""
    if KEY_FILE.exists():
        try:
            os.remove(KEY_FILE)
            print("Success: API Key has been removed.")
        except Exception as e:
            print(f"Error: Failed to remove API key: {e}")
    else:
        print("No stored API key found to remove.")