import os

# Reduce noisy STDERR logs from gRPC/absl before importing Google SDKs.
# These settings aim to suppress INFO/WARNING/ERROR logs emitted by native libs
# that happen prior to Python log initialization.
os.environ.setdefault("GRPC_VERBOSITY", "ERROR")
os.environ.setdefault("GRPC_LOG_SEVERITY", "ERROR")
# Abseil logging (used by some Google native deps). 3 ~ FATAL-only
os.environ.setdefault("ABSL_LOGGING_MIN_LOG_LEVEL", "3")
# glog compatibility (some builds respect this env var)
os.environ.setdefault("GLOG_minloglevel", "3")

import google.generativeai as genai
import time
from . import config, ui

DEFAULT_MODEL = os.getenv("PAI_MODEL", "gemini-2.5-flash")
try:
    DEFAULT_TEMPERATURE = float(os.getenv("PAI_TEMPERATURE", "0.4"))
except ValueError:
    DEFAULT_TEMPERATURE = 0.4

# Global model holder and settings
model = None
_current_model_name = None
_current_temperature = None
_current_api_key_fingerprint = None

def _configure_with_key(api_key: str, model_name: str, temperature: float):
    global model, _current_model_name, _current_temperature, _current_api_key_fingerprint
    genai.configure(api_key=api_key)
    generation_config = {"temperature": temperature}
    model = genai.GenerativeModel(model_name, generation_config=generation_config)
    _current_model_name = model_name
    _current_temperature = temperature
    _current_api_key_fingerprint = f"{api_key[:6]}...{api_key[-4:]}"

def _get_next_enabled_key() -> str | None:
    keys = config.get_enabled_keys()
    if not keys:
        return None
    rr = config.get_rr_index()
    idx = rr % len(keys)
    api_key = keys[idx].get("key")
    # advance rr
    config.set_rr_index(rr + 1)
    return api_key

def set_runtime_model(model_name: str | None = None, temperature: float | None = None):
    """Configure or reconfigure the GenerativeModel at runtime.

    This reads the API key from config and constructs a new GenerativeModel
    using the provided (or default) model name and temperature.
    """
    global model
    name = (model_name or DEFAULT_MODEL) or "gemini-2.5-flash"
    try:
        temp = DEFAULT_TEMPERATURE if temperature is None else float(temperature)
    except ValueError:
        temp = DEFAULT_TEMPERATURE
    api_key = _get_next_enabled_key() or config.get_api_key()
    if not api_key:
        ui.print_error("Error: API Key is not configured. Please run `pai config --set <YOUR_API_KEY>` or add keys with `pai config --add <KEY>`.")
        model = None
        return
    try:
        _configure_with_key(api_key, name, temp)
    except Exception as e:
        ui.print_error(f"Failed to configure the generative AI model: {e}")
        model = None

# Initialize once on import with defaults
set_runtime_model(DEFAULT_MODEL, DEFAULT_TEMPERATURE)

def generate_text(prompt: str) -> str:
    """Sends a prompt to the Gemini API and returns the text response, with round-robin retries across API keys."""
    # Ensure model is configured
    if not model:
        set_runtime_model(_current_model_name or DEFAULT_MODEL, _current_temperature or DEFAULT_TEMPERATURE)
        if not model:
            error_message = "Error: API Key or model is not configured. Please run `pai config --set <YOUR_API_KEY>` and try again."
            ui.print_error(error_message)
            return error_message

    # Try across enabled keys (up to N retries)
    enabled = config.get_enabled_keys()
    max_attempts = max(1, len(enabled))

    last_error = None
    for attempt in range(max_attempts):
        try:
            with ui.console.status("[bold yellow]Agent is thinking...", spinner="dots"):
                response = model.generate_content(prompt)

            cleaned_text = response.text.strip()
            if cleaned_text.startswith("```python"):
                cleaned_text = cleaned_text[len("```python"):].strip()
            elif cleaned_text.startswith("```json"):
                cleaned_text = cleaned_text[len("```json"):].strip()
            elif cleaned_text.startswith("```"):
                cleaned_text = cleaned_text[len("```"):].strip()

            if cleaned_text.endswith("```"):
                cleaned_text = cleaned_text[:-len("```")].strip()
            
            return cleaned_text
        except Exception as e:
            last_error = e
            # Try rotate to next key and reconfigure
            next_key = _get_next_enabled_key()
            if not next_key:
                break
            try:
                _configure_with_key(next_key, _current_model_name or DEFAULT_MODEL, _current_temperature or DEFAULT_TEMPERATURE)
            except Exception as cfg_err:
                last_error = cfg_err
                continue

    ui.print_error(f"Error: An issue occurred with the LLM API: {last_error}")
    return ""

def generate_text_resilient(prompt: str) -> str:
    """Robust text generation with time-based retries and exponential backoff.

    Behavior:
    - Calls generate_text() repeatedly until a non-empty response is obtained
      or the maximum number of retries is reached.
    - Backoff doubles each attempt, starting from 1s up to 8s.
    - Max attempts configurable via env PAI_MAX_INFERENCE_RETRIES (default 8).
    """
    try:
        max_attempts = int(os.getenv("PAI_MAX_INFERENCE_RETRIES", "8"))
    except ValueError:
        max_attempts = 8
    max_attempts = max(1, min(max_attempts, 50))

    delay = 1.0
    for attempt in range(1, max_attempts + 1):
        text = generate_text(prompt)
        if isinstance(text, str) and text.strip() and not text.strip().startswith("Error:"):
            return text
        if attempt < max_attempts:
            # brief status to UI and wait
            ui.print_warning(f"Inference attempt {attempt}/{max_attempts} failed; retrying in {int(delay)}s...")
            try:
                time.sleep(delay)
            except Exception:
                pass
            delay = min(delay * 2, 8.0)
    # Final attempt failed
    ui.print_error("Exceeded maximum inference retries. Returning empty result.")
    return ""