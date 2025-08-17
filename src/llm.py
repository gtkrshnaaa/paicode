import google.generativeai as genai
from . import config, ui

# Get the API key from our config module
API_KEY = config.get_api_key()

# Initialize the model only if the API Key exists
model = None
if API_KEY:
    try:
        genai.configure(api_key=API_KEY)
        model = genai.GenerativeModel('gemini-2.5-flash')
    except Exception as e:
        ui.print_error(f"Failed to configure the generative AI model: {e}")
else:
    # Do nothing on load; the error will be handled when a function is called
    pass 

def generate_text(prompt: str) -> str:
    """Sends a prompt to the Gemini API and returns the text response."""
    if not model:
        error_message = "Error: API Key is not configured. Please run `pai config --set <YOUR_API_KEY>` to set it up."
        ui.print_error(error_message)
        return error_message

    try:
        with ui.console.status("[bold yellow]Agent is thinking...", spinner="dots"):
            response = model.generate_content(prompt)
        
        # Clean the output from markdown code blocks if they exist
        cleaned_text = response.text.strip()
        if cleaned_text.startswith("```python"):
            cleaned_text = cleaned_text[len("```python"):].strip()
        elif cleaned_text.startswith("```"):
            cleaned_text = cleaned_text[len("```"):].strip()

        if cleaned_text.endswith("```"):
            cleaned_text = cleaned_text[:-len("```")].strip()
            
        return cleaned_text
    except Exception as e:
        ui.print_error(f"Error: An issue occurred with the LLM API: {e}")
        return ""