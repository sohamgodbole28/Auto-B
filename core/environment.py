"""
Environment validation module.
"""

import shutil
from rich.console import Console
from rich.table import Table

SUPPORTED_TOOLS = [
    "subfinder",
    "assetfinder",
    "amass",
    "httpx",
    "katana",
    "gau",
    "waybackurls",
    "nuclei",
    "ffuf",
    "dalfox",
    "naabu"
]

class EnvironmentValidator:
    """Validates the system environment for required tools."""

    def __init__(self) -> None:
        self.console = Console()
        self.installed_count = 0
        self.missing_count = 0
        self.results: dict[str, bool] = {}

    def check_tools(self) -> None:
        """Checks for the presence of supported tools."""
        self.installed_count = 0
        self.missing_count = 0
        self.results.clear()

        for tool in SUPPORTED_TOOLS:
            is_installed = shutil.which(tool) is not None
            self.results[tool] = is_installed
            if is_installed:
                self.installed_count += 1
            else:
                self.missing_count += 1

    def display_results(self) -> None:
        """Displays a Rich table with the validation results."""
        table = Table(title="Environment Validation")
        table.add_column("Tool", style="cyan", no_wrap=True)
        table.add_column("Status", style="magenta")

        for tool, is_installed in self.results.items():
            if is_installed:
                status = "[green]✔ Installed[/green]"
            else:
                status = "[red]✖ Missing[/red]"
            table.add_row(tool, status)

        self.console.print(table)
        
        self.console.print(f"\n[bold]Summary:[/bold]")
        self.console.print(f"[green]Total Installed: {self.installed_count}[/green]")
        self.console.print(f"[red]Total Missing: {self.missing_count}[/red]")
