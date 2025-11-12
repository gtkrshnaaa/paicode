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
    """Configure or reconfigure the GenerativeModel at runtime.

    This reads the API key from config and constructs a new GenerativeModel
    using the provided (or default) model name and temperature.
    """
    global model, _runtime
    # Only update the runtime preferred name/temperature; API key will be injected per call (round-robin)
    try:
        name = (model_name or DEFAULT_MODEL) or "gemini-2.5-flash-lite"
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

def _prepare_runtime() -> tuple[bool, str]:
    """Configure API key via smart rotation and ensure model object exists.
    
    Returns:
        Tuple of (success: bool, key_id: str). If success is False, key_id is empty.
    """
    global model
    
    # Use smart key selection (skips blacklisted keys)
    pair = config.get_next_available_key()
    
    if pair is None:
        # Check if all keys are blacklisted
        blacklist_status = config.get_blacklist_status()
        if blacklist_status:
            # All keys are rate limited
            min_remaining = min(blacklist_status.values())
            minutes = int(min_remaining / 60)
            seconds = int(min_remaining % 60)
            ui.print_error(f"Error: All API keys are rate limited. Retry in {minutes}m {seconds}s.")
        else:
            # No keys configured at all
            ui.print_error("Error: No API keys configured. Use `pai config add <ID> <API_KEY>`.")
        model = None
        return False, ""
    
    key_id, api_key = pair
    
    try:
        genai.configure(api_key=api_key)
        if model is None:
            # Build model using stored runtime prefs
            name = _runtime.get("name") or DEFAULT_MODEL
            temp = _runtime.get("temperature") if _runtime.get("temperature") is not None else DEFAULT_TEMPERATURE
            generation_config = {"temperature": temp}
            model = genai.GenerativeModel(name, generation_config=generation_config)
        return True, key_id
    except Exception as e:
        ui.print_error(f"Failed to configure API key '{key_id}': {e}")
        model = None
        return False, ""

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

def generate_text(prompt: str, max_retries: int = 3) -> str:
    """Sends a prompt to the Gemini API with automatic retry on rate limit.
    
    This function implements smart retry logic:
    1. Tries with current available API key
    2. If rate limit is hit, blacklists that key for 10 minutes
    3. Automatically retries with next available key
    4. Repeats up to max_retries times
    5. User doesn't need to do anything - it's fully automatic
    
    Args:
        prompt: The prompt to send to the LLM
        max_retries: Maximum number of retry attempts (default: 3)
        
    Returns:
        The cleaned response text, or empty string if all retries failed
    """
    
    for attempt in range(max_retries):
        # Prepare runtime with next available key
        success, current_key_id = _prepare_runtime()
        
        if not success:
            # No keys available (all blacklisted or not configured)
            return ""
        
        try:
            # Show status with current attempt info
            status_msg = "[bold yellow]Agent is thinking..."
            if attempt > 0:
                status_msg = f"[bold yellow]Retrying with different API key... (attempt {attempt + 1}/{max_retries})"
            
            with ui.console.status(status_msg, spinner="dots"):
                response = model.generate_content(prompt)
            
            # Success! Clean and return the response
            cleaned_text = _clean_response_text(response.text)
            
            # If this was a retry, show success message
            if attempt > 0:
                ui.print_success(f"✓ Successfully switched to backup API key and completed request.")
            
            return cleaned_text
            
        except Exception as e:
            # Check if it's a rate limit error
            is_rate_limit = _is_rate_limit_error(e)
            
            if is_rate_limit:
                # Blacklist this key for 10 minutes
                config.blacklist_key(current_key_id, duration_seconds=600)
                
                if attempt < max_retries - 1:
                    # Try next key with delay to avoid cascade blacklisting
                    ui.print_warning(f"⚠ Rate limit detected on key '{current_key_id}'. Switching to next API key...")
                    ui.print_info("⏳ Waiting 3 seconds to avoid cascade rate limiting...")
                    time.sleep(3)  # Delay to prevent cascade blacklisting
                    continue
                else:
                    # Final attempt failed
                    ui.print_error(f"Error: All API keys exhausted or rate limited. Please wait 10 minutes.")
                    return ""
            else:
                # Non-rate-limit error (e.g., network issue, invalid prompt)
                ui.print_error(f"Error: LLM API issue: {e}")
                
                # For non-rate-limit errors, retry once more if we have attempts left
                if attempt < max_retries - 1:
                    ui.print_warning("Retrying with same key...")
                    continue
                else:
                    return ""
    
    # Should not reach here, but just in case
    ui.print_error("Error: Maximum retry attempts reached.")
    return ""