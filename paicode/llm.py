import os
import warnings

# Reduce noisy STDERR logs from gRPC/absl before importing Google SDKs.
# These settings aim to suppress INFO/WARNING/ERROR logs emitted by native libs
# that happen prior to Python log initialization.
os.environ.setdefault("GRPC_VERBOSITY", "NONE")
os.environ.setdefault("GRPC_LOG_SEVERITY", "ERROR")
# Abseil logging (used by some Google native deps). 3 ~ FATAL-only
os.environ.setdefault("ABSL_LOGGING_MIN_LOG_LEVEL", "3")
# glog compatibility (some builds respect this env var)
os.environ.setdefault("GLOG_minloglevel", "3")
# Additional environment variables to suppress Google SDK warnings
os.environ.setdefault("GOOGLE_CLOUD_DISABLE_GRPC", "true")
os.environ.setdefault("GRPC_ENABLE_FORK_SUPPORT", "false")

# Suppress specific warnings
warnings.filterwarnings("ignore", category=UserWarning, module="google")
warnings.filterwarnings("ignore", message=".*ALTS.*")
warnings.filterwarnings("ignore", message=".*log messages before absl::InitializeLog.*")

import google.generativeai as genai
from . import config, ui

DEFAULT_MODEL = os.getenv("PAI_MODEL", "gemini-2.5-flash")
try:
    DEFAULT_TEMPERATURE = float(os.getenv("PAI_TEMPERATURE", "0.3"))
    # Clamp temperature to safe range
    if DEFAULT_TEMPERATURE < 0.0:
        DEFAULT_TEMPERATURE = 0.0
    elif DEFAULT_TEMPERATURE > 2.0:
        DEFAULT_TEMPERATURE = 2.0
except ValueError:
    DEFAULT_TEMPERATURE = 0.3

# Global model holder
model = None
_runtime = {
    "name": None,
    "temperature": None,
}

def set_runtime_model(model_name: str | None = None, temperature: float | None = None):
    """Configure or reconfigure the GenerativeModel at runtime.

    This reads the API key from config and constructs a new GenerativeModel
    using the provided (or default) model name and temperature.
    """
    global model, _runtime
    # Only update the runtime preferred name/temperature; API key will be injected per call (round-robin)
    try:
        name = (model_name or DEFAULT_MODEL) or "gemini-2.5-flash"
        temp = DEFAULT_TEMPERATURE if temperature is None else float(temperature)
        # Clamp temperature to safe range
        temp = max(0.0, min(2.0, temp))
        _runtime["name"] = name
        _runtime["temperature"] = temp
        # (Re)build model object shell; API key is configured on each request
        generation_config = {"temperature": temp}
        model = genai.GenerativeModel(name, generation_config=generation_config)
    except Exception as e:
        ui.print_error(f"Failed to configure the generative AI model: {e}")
        model = None

# Initialize once on import with defaults
set_runtime_model(DEFAULT_MODEL, DEFAULT_TEMPERATURE)

def _prepare_runtime() -> bool:
    """Configure API key via round-robin and ensure model object exists."""
    global model
    # Try round-robin key first
    pair = config.next_api_key()
    api_key = None
    if pair is not None:
        _, api_key = pair
    if not api_key:
        api_key = config.get_api_key()
    if not api_key:
        ui.print_error("Error: No API keys configured. Use `pai config add <ID> <API_KEY>`.")
        model = None
        return False
    try:
        genai.configure(api_key=api_key)
        if model is None:
            # build model using stored runtime prefs
            name = _runtime.get("name") or DEFAULT_MODEL
            temp = _runtime.get("temperature") if _runtime.get("temperature") is not None else DEFAULT_TEMPERATURE
            generation_config = {"temperature": temp}
            model = genai.GenerativeModel(name, generation_config=generation_config)
        return True
    except Exception as e:
        ui.print_error(f"Failed to set API key or build model: {e}")
        model = None
        return False

def generate_text(prompt: str) -> str:
    """Sends a prompt to the Gemini API and returns the text response."""
    if not _prepare_runtime():
        return ""

    try:
        with ui.console.status("[bold yellow]Agent is thinking...", spinner="dots"):
            response = model.generate_content(prompt)
        
        # Clean the output from markdown code blocks if they exist
        cleaned_text = response.text.strip()
        
        # Remove all common markdown code block patterns
        # Handle language-specific code blocks
        code_block_prefixes = [
            "```python", "```html", "```css", "```javascript", "```js",
            "```typescript", "```ts", "```json", "```yaml", "```yml",
            "```bash", "```sh", "```diff", "```xml", "```sql",
            "```java", "```cpp", "```c", "```go", "```rust", "```ruby",
            "```php", "```markdown", "```md", "```text", "```txt", "```"
        ]
        
        for prefix in code_block_prefixes:
            if cleaned_text.startswith(prefix):
                cleaned_text = cleaned_text[len(prefix):].strip()
                break
        
        # Remove trailing code block markers
        if cleaned_text.endswith("```"):
            cleaned_text = cleaned_text[:-len("```")].strip()
        
        # Remove any remaining language tags at the start (e.g., "html", "json")
        lines = cleaned_text.split('\n')
        if lines and len(lines[0].strip()) < 20 and lines[0].strip().lower() in [
            'html', 'css', 'javascript', 'js', 'python', 'json', 'yaml', 
            'bash', 'sh', 'diff', 'xml', 'sql', 'java', 'cpp', 'c', 'go', 
            'rust', 'ruby', 'php', 'markdown', 'md', 'text', 'txt', 'on'
        ]:
            cleaned_text = '\n'.join(lines[1:]).strip()
        
        # Additional cleanup for markdown formatting in text
        # Remove markdown bold/italic markers if they appear to be artifacts
        if cleaned_text.count('**') > 0 or cleaned_text.count('*') > 10:
            # This might be markdown formatting, but only clean if it looks excessive
            pass  # Keep for now, as some legitimate content uses these
            
        return cleaned_text
    except Exception as e:
        ui.print_error(f"Error: An issue occurred with the LLM API: {e}")
        return ""