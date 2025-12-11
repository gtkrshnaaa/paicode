import os
import warnings
import time

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

DEFAULT_MODEL = os.getenv("PAI_MODEL", "gemini-2.5-flash-lite")
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
    """Set the runtime model configuration."""
    global model, _runtime
    
    # Update runtime settings
    if model_name is not None:
        _runtime["name"] = model_name
    if temperature is not None:
        temperature = max(0.0, min(2.0, temperature))
        _runtime["temperature"] = temperature
    
    # Reset model so it gets recreated with new settings on next use
    model = None

# Initialize runtime settings (model will be created when needed)
_runtime = {
    "name": DEFAULT_MODEL,
    "temperature": DEFAULT_TEMPERATURE
}

def _prepare_runtime() -> bool:
    """Configure API key and ensure model object exists.
    
    Returns:
        bool: True if successful, False otherwise.
    """
    global model
    
    # Get single API key
    api_key = config.get_api_key()
    
    if not api_key:
        ui.print_error("Error: No API key configured. Use 'pai config set <API_KEY>'.")
        model = None
        return False
    
    try:
        # CRITICAL FIX: Always reconfigure API key to ensure fresh credential
        # This prevents caching issues when API key is changed during runtime
        genai.configure(api_key=api_key)
        
        # CRITICAL FIX: Always create a new model instance
        # This ensures the model object uses the latest API key configuration
        # Same approach as googleapikeytesting/rolling_test.py for consistency
        name = _runtime.get("name") or DEFAULT_MODEL
        temp = _runtime.get("temperature") if _runtime.get("temperature") is not None else DEFAULT_TEMPERATURE
        generation_config = {"temperature": temp}
        model = genai.GenerativeModel(name, generation_config=generation_config)
        
        return True
    except Exception as e:
        ui.print_error(f"Failed to configure API key: {e}")
        model = None
        return False

def _is_rate_limit_error(error: Exception) -> bool:
    """Detect if an exception is a rate limit error.
    
    Args:
        error: The exception to check
        
    Returns:
        True if it's a rate limit error, False otherwise
    """
    error_msg = str(error).lower()
    
    # Common rate limit indicators
    rate_limit_keywords = [
        'rate limit', 'rate_limit', 'ratelimit',
        'quota', 'quota exceeded',
        'resource exhausted', 'resourceexhausted',
        '429', 'too many requests',
        'limit exceeded', 'requests per minute'
    ]
    
    return any(keyword in error_msg for keyword in rate_limit_keywords)

def _clean_response_text(text: str) -> str:
    """Clean markdown artifacts from LLM response.
    
    Args:
        text: Raw response text from LLM
        
    Returns:
        Cleaned text without markdown code blocks
    """
    cleaned_text = text.strip()
    
    # Remove all common markdown code block patterns
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
    
    # Remove any remaining language tags at the start
    lines = cleaned_text.split('\n')
    if lines and len(lines[0].strip()) < 20 and lines[0].strip().lower() in [
        'html', 'css', 'javascript', 'js', 'python', 'json', 'yaml', 
        'bash', 'sh', 'diff', 'xml', 'sql', 'java', 'cpp', 'c', 'go', 
        'rust', 'ruby', 'php', 'markdown', 'md', 'text', 'txt', 'on'
    ]:
        cleaned_text = '\n'.join(lines[1:]).strip()
    
    return cleaned_text

def generate_text(prompt: str, call_purpose: str = "thinking") -> str:
    """
    Generate text with single API key - optimized for 2-call system.
    
    Args:
        prompt: The prompt to send to the LLM
        call_purpose: Purpose of the call for logging (e.g., "planning", "execution")
        
    Returns:
        The cleaned response text, or empty string if failed
    """
    global model
    
    # Ensure model is configured
    if model is None:
        if not _prepare_runtime():
            return ""
    
    try:
        # Show status with purpose
        status_msg = f"[bold yellow]Agent {call_purpose}..."
        
        with ui.console.status(status_msg, spinner="dots"):
            response = model.generate_content(prompt)
        
        # Success! Clean and return the response
        cleaned_text = _clean_response_text(response.text)
        
        # Log token usage if available (for optimization)
        if hasattr(response, 'usage_metadata'):
            usage = response.usage_metadata
            ui.print_info(f"Tokens: {usage.prompt_token_count} → {usage.candidates_token_count}")
        
        return cleaned_text
        
    except Exception as e:
        is_rate_limit = _is_rate_limit_error(e)
        
        if is_rate_limit:
            ui.print_error("✗ Rate limit reached. Please wait a few minutes before trying again.")
            ui.print_info("Consider using a different API key if available.")
        else:
            ui.print_error(f"✗ LLM API error: {e}")
        
        return ""

def test_api_connection() -> bool:
    """Test if API connection works."""
    test_response = generate_text("Say 'Hello' if you can hear me.", "connection test")
    return len(test_response) > 0