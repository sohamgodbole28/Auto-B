"""
UI Progress Tracker module.
"""

from datetime import datetime
from rich.console import Console

from core.events import (
    EventBus,
    StageStarted,
    StageFinished,
    StageSkipped,
    WorkflowStarted
)

class UIProgressTracker:
    """Subscribes to EventBus to render progress independently of Engine."""
    
    def __init__(self, event_bus: EventBus) -> None:
        self.console = Console()
        self.event_bus = event_bus
        self.start_times = {}
        
        self.event_bus.subscribe(StageStarted, self._on_stage_started)
        self.event_bus.subscribe(StageFinished, self._on_stage_finished)
        self.event_bus.subscribe(StageSkipped, self._on_stage_skipped)
        self.event_bus.subscribe(WorkflowStarted, self._on_workflow_started)

    def _on_workflow_started(self, event: WorkflowStarted) -> None:
        self.console.print(f"\n[bold blue]Starting Workflow:[/bold blue] {event.workflow_name}")

    def _on_stage_started(self, event: StageStarted) -> None:
        self.start_times[event.stage_name] = datetime.now()

    def _on_stage_finished(self, event: StageFinished) -> None:
        start_time = self.start_times.get(event.stage_name, datetime.now())
        end_time = datetime.now()
        
        if event.success:
            if event.empty_output:
                status = "[yellow]EMPTY OUTPUT[/yellow]"
            else:
                status = "[green]SUCCESS[/green]"
        else:
            status = "[red]FAILED[/red]"
        
        self.console.print("-" * 48)
        self.console.print(f"Running:\n{event.stage_name}\n")
        self.console.print(f"Started:\n{start_time.strftime('%H:%M:%S')}\n")
        self.console.print(f"Finished:\n{end_time.strftime('%H:%M:%S')}\n")
        self.console.print(f"Duration:\n{event.duration:.2f} seconds\n")
        self.console.print(f"Status:\n{status}")
        self.console.print("-" * 48)

    def _on_stage_skipped(self, event: StageSkipped) -> None:
        self.console.print("-" * 48)
        self.console.print(f"Running:\n{event.stage_name}\n")
        self.console.print(f"Status:\n[yellow]SKIPPED ({event.reason})[/yellow]")
        self.console.print("-" * 48)
