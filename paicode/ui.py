from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.theme import Theme
from rich.rule import Rule
from rich.box import ROUNDED
from rich.text import Text

# Define a custom theme for consistency
custom_theme = Theme({
    "info": "dim cyan",
    "success": "bold green",
    "warning": "yellow",
    "error": "bold red",
    "action": "bold blue",
    "path": "underline italic bright_blue"
})

# Create a single console instance to be used across the application
console = Console(theme=custom_theme)

def print_success(message: str):
    """Displays a success message with a checkmark icon."""
    console.print(f"[success]✓ {message}[/success]")

def print_error(message: str):
    """Displays an error message with a cross icon."""
    console.print(f"[error]✗ {message}[/error]")

def print_warning(message: str):
    """Displays a warning message."""
    console.print(f"[warning]! {message}[/warning]")

def print_info(message: str):
    """Displays an informational message."""
    console.print(f"[info]i {message}[/info]")
    
def print_action(message: str):
    """Displays an action being performed by the agent."""
    console.print(f"[action]-> {message}[/action]")

def display_panel(content: str, title: str, language: str = None):
    """Displays content within a panel, with optional syntax highlighting."""
    if language:
        # Use Syntax for code highlighting
        display_content = Syntax(content, language, theme="monkai", line_numbers=True)
    else:
        display_content = content
    
    console.print(Panel(display_content, title=f"[bold cyan]{title}[/bold cyan]", border_style="cyan", expand=False))

def print_rule(title: str):
    """Displays a horizontal rule with a title."""
    console.print(Rule(f"[bold]{title}[/bold]", style="cyan"))

def print_panel_title(title: str):
    """Displays a styled title inside a rounded panel."""
    console.print(
        Panel(
            Text(title, justify="center", style="bold"),
            box=ROUNDED,
            border_style="cyan",
            expand=False
        )
    )