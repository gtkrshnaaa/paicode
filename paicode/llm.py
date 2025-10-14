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
import asyncio
from functools import partial

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
_last_error: Exception | None = None
_last_error_rate_limited: bool = False

def _is_rate_limit_error(err: Exception) -> bool:
    """Best-effort detection of rate limit / quota errors from the provider.

    We avoid tight coupling to SDK exception types and rely on message patterns.
    """
    try:
        s = str(err).lower()
    except Exception:
        s = ""
    keywords = [
        "rate limit", "quota", "429", "resource has been exhausted",
        "exceeded", "quota_exceeded", "too many requests"
    ]
    return any(k in s for k in keywords)

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

def _is_task_likely_complete(original_request: str, current_response: str, history: list) -> bool:
    """Use LLM to assess if task is likely complete based on request and responses"""
    try:
        # Quick assessment prompt
        assessment_prompt = f"""
Original user task: "{original_request}"
Latest response: "{current_response[:400]}..."
Response history: {len(history)} attempts

Is the user's task completed based on the latest response? 
Answer only: "COMPLETE" if finished, "CONTINUE" if still needs work.
"""
        assessment = generate_text(assessment_prompt)
        return "COMPLETE" in assessment.upper()
    except Exception:
        return False

def _should_continue_inference(original_request: str, history: list, current_attempt: int, max_attempts: int) -> bool:
    """Assess whether to continue inference beyond mid-point"""
    try:
        recent_responses = [r for r in history[-3:] if not r.startswith("ERROR_ATTEMPT")]
        if not recent_responses:
            return True  # No good responses yet, keep trying
            
        assessment_prompt = f"""
Task: "{original_request}"
Current progress: {current_attempt}/{max_attempts} iterations.
Recent responses: {recent_responses}

Should inference continue? Answer "YES" or "NO" with brief reason.
"""
        assessment = generate_text(assessment_prompt)
        return "YES" in assessment.upper() or "CONTINUE" in assessment.upper()
    except Exception:
        return True  # Default to continue if assessment fails

def _should_request_continuation(original_request: str, last_response: str, max_attempts: int) -> bool:
    """Decide if we should ask user for continuation beyond max attempts"""
    try:
        continuation_prompt = f"""
Task: "{original_request}"
Last response after {max_attempts} iterations: "{last_response[:300]}..."

Does this task need to continue beyond {max_attempts} iterations?
Answer "NEEDED" if still requires work, "SUFFICIENT" if already enough.
"""
        assessment = generate_text(continuation_prompt)
        return "NEEDED" in assessment.upper()
    except Exception:
        return False  # Default to not request continuation if assessment fails

def generate_text(prompt: str) -> str:
    """Sends a prompt to the Gemini API and returns the text response, with round-robin retries across API keys."""
    # Ensure model is configured
    global _last_error, _last_error_rate_limited
    _last_error = None
    _last_error_rate_limited = False
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
            _last_error = e
            # If looks like rate limit, inform the user and try next key/backoff in resilient wrapper
            if _is_rate_limit_error(e):
                _last_error_rate_limited = True
                ui.print_warning("LLM API is rate-limited or quota exceeded; attempting fallback key/next retry...")
            # Try rotate to next key and reconfigure
            next_key = _get_next_enabled_key()
            if not next_key:
                break
            try:
                _configure_with_key(next_key, _current_model_name or DEFAULT_MODEL, _current_temperature or DEFAULT_TEMPERATURE)
            except Exception as cfg_err:
                last_error = cfg_err
                continue

    if last_error and _is_rate_limit_error(last_error):
        _last_error_rate_limited = True
        ui.print_warning("LLM API appears to be rate-limited or quota-exceeded. Please wait a moment or add more API keys (pai config add).")
    ui.print_error(f"Error: An issue occurred with the LLM API: {last_error}")
    return ""

def generate_text_resilient(prompt: str, original_request: str = None) -> str:
    """Robust text generation with intelligent retry and task completion awareness.

    Behavior:
    - Calls generate_text() repeatedly until a non-empty response is obtained
      or the maximum number of retries is reached.
    - Uses LLM intelligence to assess if task is complete before max retries
    - Backoff doubles each attempt, starting from 1s up to 8s.
    - Max attempts configurable via env PAI_MAX_INFERENCE_RETRIES (default 25).
    """
    try:
        max_attempts = int(os.getenv("PAI_MAX_INFERENCE_RETRIES", "25"))
    except ValueError:
        max_attempts = 25
    max_attempts = max(1, min(max_attempts, 50))

    delay = 1.0
    responses_history = []
    
    for attempt in range(1, max_attempts + 1):
        text = generate_text(prompt)
        
        if isinstance(text, str) and text.strip() and not text.strip().startswith("Error:"):
            responses_history.append(text)
            
            # Smart completion check: After attempt 3, check if task is complete
            if attempt >= 3 and original_request and len(responses_history) >= 2:
                if _is_task_likely_complete(original_request, text, responses_history):
                    ui.print_info(f"✓ Task appears complete after {attempt} iterations. Stopping inference.")
                    return text
            
            return text
            
        # Handle failure
        responses_history.append(f"ERROR_ATTEMPT_{attempt}: {text}")
        
        # Smart continuation decision after 15 attempts
        if attempt == 15 and original_request:
            should_continue = _should_continue_inference(original_request, responses_history, attempt, max_attempts)
            if not should_continue:
                ui.print_warning("Task evaluation indicates no need to continue. Stopping inference.")
                return text or ""
        
        # Decide message based on last error flags
        if attempt < max_attempts:
            if _last_error_rate_limited:
                ui.print_warning(f"Rate limit/quota detected (attempt {attempt}/{max_attempts}); retrying in {int(delay)}s...")
            else:
                ui.print_warning(f"Inference attempt {attempt}/{max_attempts} failed; retrying in {int(delay)}s...")
            try:
                time.sleep(delay)
            except Exception:
                pass
            delay = min(delay * 2, 8.0)
    
    # Reached max attempts - ask for continuation if task seems incomplete
    if original_request and responses_history:
        last_response = responses_history[-1] if responses_history else ""
        if _should_request_continuation(original_request, last_response, max_attempts):
            ui.print_warning(f"Reached {max_attempts} iterations but task incomplete. Continue with 'y' or stop with 'n'.")
            # Note: Actual continuation logic would be handled by caller
    
    ui.print_error("Exceeded maximum inference retries. Returning empty result.")
    return ""

# ---------------- Async variants ----------------
async def async_generate_text(prompt: str) -> str:
    """Async version of generate_text using run_in_executor for the blocking SDK call."""
    global _last_error, _last_error_rate_limited
    _last_error = None
    _last_error_rate_limited = False
    if not model:
        set_runtime_model(_current_model_name or DEFAULT_MODEL, _current_temperature or DEFAULT_TEMPERATURE)
        if not model:
            error_message = "Error: API Key or model is not configured. Please run `pai config --set <YOUR_API_KEY>` and try again."
            ui.print_error(error_message)
            return error_message

    enabled = config.get_enabled_keys()
    max_attempts = max(1, len(enabled))

    loop = asyncio.get_running_loop()
    last_error = None
    for attempt in range(max_attempts):
        try:
            with ui.console.status("[bold yellow]Agent is thinking...", spinner="dots"):
                # Wrap the blocking call in a thread to avoid blocking the event loop
                response = await loop.run_in_executor(None, partial(model.generate_content, prompt))
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
            _last_error = e
            if _is_rate_limit_error(e):
                _last_error_rate_limited = True
                ui.print_warning("LLM API is rate-limited or quota exceeded; attempting fallback key/next retry...")
            next_key = _get_next_enabled_key()
            if not next_key:
                break
            try:
                _configure_with_key(next_key, _current_model_name or DEFAULT_MODEL, _current_temperature or DEFAULT_TEMPERATURE)
            except Exception as cfg_err:
                last_error = cfg_err
                continue

    if last_error and _is_rate_limit_error(last_error):
        _last_error_rate_limited = True
        ui.print_warning("LLM API appears to be rate-limited or quota-exceeded. Please wait a moment or add more API keys (pai config add).")
    ui.print_error(f"Error: An issue occurred with the LLM API: {last_error}")
    return ""

async def async_generate_text_resilient(prompt: str, original_request: str = None) -> str:
    """Async resilient generation with intelligent task completion awareness."""
    try:
        max_attempts = int(os.getenv("PAI_MAX_INFERENCE_RETRIES", "25"))
    except ValueError:
        max_attempts = 25
    max_attempts = max(1, min(max_attempts, 50))

    delay = 1.0
    responses_history = []
    
    for attempt in range(1, max_attempts + 1):
        text = await async_generate_text(prompt)
        
        if isinstance(text, str) and text.strip() and not text.strip().startswith("Error:"):
            responses_history.append(text)
            
            # Smart completion check after attempt 3
            if attempt >= 3 and original_request and len(responses_history) >= 2:
                if _is_task_likely_complete(original_request, text, responses_history):
                    ui.print_info(f"✓ Task appears complete after {attempt} iterations. Stopping inference.")
                    return text
            
            return text
            
        # Handle failure
        responses_history.append(f"ERROR_ATTEMPT_{attempt}: {text}")
        
        # Smart continuation decision after 15 attempts
        if attempt == 15 and original_request:
            should_continue = _should_continue_inference(original_request, responses_history, attempt, max_attempts)
            if not should_continue:
                ui.print_warning("Task evaluation indicates no need to continue. Stopping inference.")
                return text or ""
        
        if attempt < max_attempts:
            if _last_error_rate_limited:
                ui.print_warning(f"Rate limit/quota detected (attempt {attempt}/{max_attempts}); retrying in {int(delay)}s...")
            else:
                ui.print_warning(f"Inference attempt {attempt}/{max_attempts} failed; retrying in {int(delay)}s...")
            try:
                await asyncio.sleep(delay)
            except Exception:
                pass
            delay = min(delay * 2, 8.0)
    
    # Reached max attempts - assess continuation need
    if original_request and responses_history:
        last_response = responses_history[-1] if responses_history else ""
        if _should_request_continuation(original_request, last_response, max_attempts):
            ui.print_warning(f"Reached {max_attempts} iterations but task incomplete. Continue with 'y' or stop with 'n'.")
    
    ui.print_error("Exceeded maximum inference retries. Returning empty result.")
    return ""