"""
Main entry point for Auto-B.
"""

import typer
from rich.console import Console
import sys

from core.context import AppContext
from menu.menu import CLI
from engine.engine import Engine

app = typer.Typer(help="Auto-B: Automated Bug Bounty Workflow Engine", add_completion=False)
console = Console()

def get_context() -> AppContext:
    """Helper to initialize and return the application context."""
    return AppContext()

@app.command()
def check_env() -> None:
    """Validates the environment to check for installed tools."""
    context = get_context()
    cli = CLI(context)
    cli.run_env_check()

@app.command()
def test_framework() -> None:
    """Tests the core framework components via the Engine."""
    context = get_context()
    console.print("\n[bold yellow]Testing Core Framework & Engine...[/bold yellow]")
    
    engine = Engine(context)
    
    try:
        # Load the dummy workflow and execute it
        engine.execute_workflow_by_name("dummy")
        console.print("[green]Dummy Workflow executed successfully![/green]")
    except Exception as e:
        console.print(f"[red]Framework test failed![/red] {e}")
        sys.exit(1)

@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """Auto-B CLI Application."""
    if ctx.invoked_subcommand is None:
        context = get_context()
        cli = CLI(context)
        cli.start_interactive()

if __name__ == "__main__":
    app()
