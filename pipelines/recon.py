"""
Reconnaissance Pipeline.
"""

import os
import glob
from datetime import datetime
import questionary
from rich.console import Console
from rich.table import Table

from engine.engine import Engine
from core.events import WorkflowStarted, WorkflowFinished

class ReconPipeline:
    """Coordinator for the Reconnaissance Workflow."""

    def __init__(self, engine: Engine) -> None:
        self.engine = engine
        self.context = engine.context
        self.console = Console()
        self.stats = {
            "executed": 0,
            "successful": 0,
            "failed": 0,
            "skipped": 0,
            "files_generated": 0
        }

    def execute(self) -> None:
        """Prepares, executes, and post-processes the recon workflow."""
        target = questionary.text("Enter Target Domain (e.g., example.com):").ask()
        if not target:
            return

        workflow = self.engine.get_workflow("recon")
        
        # Publish Workflow Started
        self.context.events.publish(WorkflowStarted(workflow_name=workflow.name))
        
        # OutputDirectory validation (create before first stage)
        self.context.output.create_workflow_dir(target, workflow.output_directory or "recon")
        
        self.context.timer.start()
        start_time = datetime.now()

        # Execute stages
        for stage in workflow.steps:
            context_vars = {"TARGET": target}
            skip = False

            # Pre-processing & Variable mapping
            if stage.name in ["subfinder", "assetfinder", "amass", "github-subdomains"]:
                output_file = self.context.output.resolve_output_path(target, "recon", f"{stage.name}.txt")
                context_vars["OUTPUT"] = output_file
                
            elif stage.name in ["dnsx", "shuffledns"]:
                input_file = self.context.output.resolve_output_path(target, "recon", "subdomains.txt")
                if not os.path.exists(input_file):
                    self.context.logger.log_warning(f"Missing input {input_file} for {stage.name}. Skipping dependent stage.")
                    self.stats["skipped"] += 1
                    skip = True
                
                context_vars["INPUT"] = input_file
                context_vars["OUTPUT"] = self.context.output.resolve_output_path(target, "recon", f"resolved_{stage.name}.txt")
                
                if stage.name == "shuffledns":
                    resolvers_file = os.path.join(self.context.config.project_root, "resolvers.txt")
                    if os.path.exists(resolvers_file):
                        context_vars["RESOLVERS"] = resolvers_file
                    else:
                        self.context.logger.log_warning("resolvers.txt not found. Skipping shuffledns.")
                        self.stats["skipped"] += 1
                        skip = True
                        
            elif stage.name == "httpx":
                input_file = self.context.output.resolve_output_path(target, "recon", "resolved.txt")
                if not os.path.exists(input_file):
                    self.context.logger.log_warning(f"Missing input {input_file} for httpx. Skipping.")
                    self.stats["skipped"] += 1
                    skip = True
                context_vars["INPUT"] = input_file
                context_vars["OUTPUT"] = self.context.output.resolve_output_path(target, "recon", "alive.txt")
                
            elif stage.name == "katana":
                input_file = self.context.output.resolve_output_path(target, "recon", "alive.txt")
                if not os.path.exists(input_file):
                    self.context.logger.log_warning(f"Missing input {input_file} for katana. Skipping.")
                    self.stats["skipped"] += 1
                    skip = True
                context_vars["INPUT"] = input_file
                context_vars["OUTPUT"] = self.context.output.resolve_output_path(target, "recon", "katana_urls.txt")
                
            elif stage.name in ["gau", "waybackurls"]:
                context_vars["OUTPUT"] = self.context.output.resolve_output_path(target, "recon", f"{stage.name}_urls.txt")
                
            elif stage.name == "uro":
                input_file = self.context.output.resolve_output_path(target, "recon", "all_urls.txt")
                if not os.path.exists(input_file):
                    self.context.logger.log_warning(f"Missing input {input_file} for uro. Skipping.")
                    self.stats["skipped"] += 1
                    skip = True
                context_vars["INPUT"] = input_file
                context_vars["OUTPUT"] = self.context.output.resolve_output_path(target, "recon", "clean_urls.txt")
                
            elif stage.name.startswith("unfurl"):
                input_file = self.context.output.resolve_output_path(target, "recon", "clean_urls.txt")
                if not os.path.exists(input_file):
                    self.context.logger.log_warning(f"Missing input {input_file} for unfurl. Skipping.")
                    self.stats["skipped"] += 1
                    skip = True
                mode = stage.name.split("_")[1] # domains, paths, parameters
                context_vars["INPUT"] = input_file
                context_vars["MODE"] = mode
                context_vars["OUTPUT"] = self.context.output.resolve_output_path(target, "recon", f"{mode}.txt")

            if skip:
                # We could publish a StageSkipped event here, but let's just continue
                continue

            # Execute via Engine
            self.stats["executed"] += 1
            result = self.engine.execute_stage(workflow.name, stage, context_vars)
            
            if result is None:
                self.stats["skipped"] += 1
                self.stats["executed"] -= 1 # Adjust since it didn't actually run
                continue
                
            if result.success:
                self.stats["successful"] += 1
            else:
                self.stats["failed"] += 1
                
            if os.path.exists(context_vars.get("OUTPUT", "")):
                self.stats["files_generated"] += 1

            # Post-processing Merges
            if stage.name == "github-subdomains":
                self._merge_subdomains(target)
            elif stage.name == "shuffledns":
                self._merge_resolved(target)
            elif stage.name == "waybackurls":
                self._merge_urls(target)

        # Publish Workflow Finished
        self.context.timer.stop()
        runtime = self.context.timer.get_total_runtime()
        self.context.events.publish(WorkflowFinished(workflow_name=workflow.name, total_runtime=runtime))
        
        self.display_summary(workflow.name, workflow.version, target, start_time, datetime.now(), runtime)

    def _merge_files(self, target: str, input_files: list, output_file_name: str) -> None:
        """Merges multiple files, removes duplicates, removes blanks, sorts."""
        merged_set = set()
        
        for file_name in input_files:
            file_path = self.context.output.resolve_output_path(target, "recon", file_name)
            if os.path.exists(file_path):
                # Ignore empty files
                if os.path.getsize(file_path) == 0:
                    continue
                with open(file_path, "r", encoding="utf-8") as f:
                    for line in f:
                        clean_line = line.strip()
                        if clean_line:
                            merged_set.add(clean_line)
                            
        output_path = self.context.output.resolve_output_path(target, "recon", output_file_name)
        with open(output_path, "w", encoding="utf-8") as f:
            for item in sorted(merged_set):
                f.write(item + "\n")
                
        if len(merged_set) == 0:
            self.context.logger.log_warning(f"All inputs were empty or missing. Generated empty output: {output_file_name}")
            
        if os.path.exists(output_path):
            self.stats["files_generated"] += 1

    def _merge_subdomains(self, target: str) -> None:
        inputs = ["subfinder.txt", "assetfinder.txt", "amass.txt", "github-subdomains.txt"]
        self._merge_files(target, inputs, "subdomains.txt")

    def _merge_resolved(self, target: str) -> None:
        inputs = ["resolved_dnsx.txt", "resolved_shuffledns.txt"]
        self._merge_files(target, inputs, "resolved.txt")

    def _merge_urls(self, target: str) -> None:
        inputs = ["katana_urls.txt", "gau_urls.txt", "waybackurls.txt"]
        self._merge_files(target, inputs, "all_urls.txt")

    def display_summary(self, workflow_name: str, version: str, target: str, start: datetime, end: datetime, runtime: float) -> None:
        """Displays the final execution summary."""
        table = Table(title="Workflow Execution Summary", show_header=False)
        
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="magenta")
        
        table.add_row("Workflow", workflow_name)
        table.add_row("Version", version)
        table.add_row("Target", target)
        table.add_row("Started", start.strftime('%Y-%m-%d %H:%M:%S'))
        table.add_row("Finished", end.strftime('%Y-%m-%d %H:%M:%S'))
        table.add_row("Total Runtime", self.context.timer.format_time(runtime))
        table.add_row("Stages Executed", str(self.stats["executed"]))
        table.add_row("Successful Stages", f"[green]{self.stats['successful']}[/green]")
        table.add_row("Failed Stages", f"[red]{self.stats['failed']}[/red]")
        table.add_row("Skipped Stages", f"[yellow]{self.stats['skipped']}[/yellow]")
        table.add_row("Files Generated", str(self.stats["files_generated"]))
        table.add_row("Output Directory", self.context.output.create_workflow_dir(target, "recon"))

        self.console.print("\n")
        self.console.print(table)
        self.console.print("\n")
