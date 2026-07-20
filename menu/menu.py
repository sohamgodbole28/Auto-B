"""
Menu module for handling CLI interactions.
"""

import sys
import questionary
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from core.context import AppContext
from core import version
from engine.engine import Engine
from menu.progress import UIProgressTracker
from pipelines.recon import ReconPipeline


class CLI:
    """Handles displaying the interactive command-line interface."""
    
    def __init__(self, context: AppContext) -> None:
        self.context = context
        self.console = Console()
        self.engine = Engine(self.context)
        self.progress_tracker = UIProgressTracker(self.context.events)

    def show_banner(self) -> None:
        """Displays the application banner."""
        banner_text = (
            f"[bold blue]{version.APP_NAME}[/bold blue] v{version.VERSION}\n"
            f"[cyan]{version.DESCRIPTION}[/cyan]\n"
            f"[italic]Author: {version.AUTHOR}[/italic]\n"
        )
        self.console.print(Panel(banner_text, expand=False, border_style="blue"))

    def run_env_check(self) -> None:
        """Runs and displays environment validation."""
        self.context.environment.check_tools()
        
        table = Table(title="Environment Validation")
        table.add_column("Tool", style="cyan", no_wrap=True)
        table.add_column("Status", style="magenta")

        for tool, is_installed in self.context.environment.results.items():
            if is_installed:
                status = "[green]✔ Installed[/green]"
            else:
                status = "[red]✖ Missing[/red]"
            table.add_row(tool, status)

        self.console.print(table)
        self.console.print(f"[green]Installed Total: {self.context.environment.installed_count}[/green]")
        self.console.print(f"[red]Missing Total: {self.context.environment.missing_count}[/red]")
        self.console.print("\n[bold]Ready[/bold]\n")

    def show_workflow_info(self, workflow_name: str) -> bool:
        """Displays metadata about a workflow before executing."""
        try:
            workflow = self.engine.loader.load_workflow(workflow_name)
        except Exception as e:
            self.console.print(f"[red]Error loading workflow:[/red] {e}")
            return False

        self.console.print("-" * 40)
        self.console.print("[bold]Workflow Information[/bold]")
        self.console.print(f"Name:              {workflow.name}")
        self.console.print(f"Description:       {workflow.description}")
        self.console.print(f"Version:           {workflow.version}")
        self.console.print(f"Author:            {workflow.author}")
        self.console.print(f"Required Tools:    {', '.join(workflow.required_tools)}")
        self.console.print(f"Estimated Runtime: {workflow.estimated_runtime}")
        
        self.console.print("-" * 40)

        return questionary.confirm("Continue?").ask()

    def start_interactive(self) -> None:
        """Starts the main interactive menu."""
        self.show_banner()
        self.run_env_check()

        choices = [
            "[1] Recon Workflow",
            "[2] Environment Check",
            "[3] Settings",
            "[0] Exit"
        ]

        while True:
            try:
                choice = questionary.select(
                    "Select an option:",
                    choices=choices,
                    instruction="(Use arrow keys, Enter to select, Ctrl+C to exit)"
                ).ask()
                
                if choice is None:
                    self.console.print("\n[yellow]Exiting gracefully...[/yellow]")
                    sys.exit(0)

                if choice.startswith("[0]"):
                    self.console.print("[yellow]Exiting Auto-B...[/yellow]")
                    sys.exit(0)
                elif choice.startswith("[1]"):
                    if self.show_workflow_info("recon"):
                        pipeline = ReconPipeline(self.engine)
                        pipeline.execute()
                elif choice.startswith("[2]"):
                    self.run_env_check()
                elif choice.startswith("[3]"):
                    self.console.print("[cyan]Settings coming soon![/cyan]")

            except KeyboardInterrupt:
                self.console.print("\n[yellow]Exiting gracefully...[/yellow]")
                sys.exit(0)
            except Exception as e:
                self.console.print(f"[bold red]An unexpected error occurred:[/bold red] {e}")
