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
from . import config, ui

DEFAULT_MODEL = os.getenv("PAI_MODEL", "gemini-2.5-flash")
try:
    DEFAULT_TEMPERATURE = float(os.getenv("PAI_TEMPERATURE", "0.4"))
except ValueError:
    DEFAULT_TEMPERATURE = 0.4

# Global model holder
model = None

def set_runtime_model(model_name: str | None = None, temperature: float | None = None):
    """Configure or reconfigure the GenerativeModel at runtime.

    This reads the API key from config and constructs a new GenerativeModel
    using the provided (or default) model name and temperature.
    """
    global model
    api_key = config.get_api_key()
    if not api_key:
        ui.print_error("Error: API Key is not configured. Please run `pai config --set <YOUR_API_KEY>` to set it up.")
        model = None
        return
    try:
        genai.configure(api_key=api_key)
        name = (model_name or DEFAULT_MODEL) or "gemini-2.5-flash"
        temp = DEFAULT_TEMPERATURE if temperature is None else float(temperature)
        generation_config = {"temperature": temp}
        model = genai.GenerativeModel(name, generation_config=generation_config)
    except Exception as e:
        ui.print_error(f"Failed to configure the generative AI model: {e}")
        model = None

# Initialize once on import with defaults
set_runtime_model(DEFAULT_MODEL, DEFAULT_TEMPERATURE)

def generate_text(prompt: str) -> str:
    """Sends a prompt to the Gemini API and returns the text response."""
    if not model:
        error_message = "Error: API Key or model is not configured. Please run `pai config --set <YOUR_API_KEY>` and try again."
        ui.print_error(error_message)
        return error_message

    try:
        with ui.console.status("[bold yellow]Agent is thinking...", spinner="dots"):
            response = model.generate_content(prompt)
        
        # Clean the output from markdown code blocks if they exist
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
        ui.print_error(f"Error: An issue occurred with the LLM API: {e}")
        return ""