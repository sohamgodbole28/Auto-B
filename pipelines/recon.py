import os
import glob
import json
import re
import platform
from datetime import datetime
import questionary
from rich.console import Console
from rich.table import Table

from engine.engine import Engine
from core.events import WorkflowStarted, WorkflowFinished, StageSkipped

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
            "timed_out": 0,
            "files_generated": 0,
            "stages_successful": [],
            "stages_failed": [],
            "stages_skipped": [],
            "stages_timed_out": []
        }
        self.intel_stats = {
            "Subdomains Discovered": 0,
            "Resolved Hosts": 0,
            "Live Hosts": 0,
            "Historical URLs": 0,
            "Clean URLs": 0,
            "JavaScript Files": 0,
            "API Endpoints": 0,
            "Login Pages": 0,
            "Admin Panels": 0,
            "Critical Hosts": 0,
            "High Hosts": 0,
            "Medium Hosts": 0,
            "Interesting Parameters": 0
        }
        
        # Deterministic Registry mapping aggregated artifacts to their contributing tools' outputs
        self.AGGREGATION_REGISTRY = {
            "subdomains.txt": [
                "subfinder.txt",
                "assetfinder.txt",
                "amass.txt",
                "github-subdomains.txt",
                "chaos.txt",
                "crt.sh.txt",
                "puredns.txt",
                "sublist3r.txt"
            ],
            "resolved.txt": [
                "resolved_dnsx.txt",
                "resolved_shuffledns.txt"
            ],
            "all_urls.txt": [
                "gau_urls.txt",
                "waybackurls_urls.txt",
                "waybackurls.txt",
                "katana_urls.txt"
            ]
        }
        self.completed_checkpoints = set()

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
            skip_reason = ""

            # ---------------------------------------------------------
            # 1. Map Inputs/Outputs
            # ---------------------------------------------------------
            if stage.name == "github-subdomains":
                if not os.environ.get("GITHUB_TOKEN"):
                    skip_reason = "GitHub token not configured."
                    skip = True
                else:
                    context_vars["OUTPUT"] = self.context.output.resolve_output_path(target, "recon", f"{stage.name}.txt")

            elif stage.name in ["subfinder", "assetfinder", "amass"]:
                context_vars["OUTPUT"] = self.context.output.resolve_output_path(target, "recon", f"{stage.name}.txt")
                
            elif stage.name in ["dnsx", "shuffledns"]:
                context_vars["INPUT"] = self.context.output.resolve_output_path(target, "recon", "subdomains.txt")
                context_vars["OUTPUT"] = self.context.output.resolve_output_path(target, "recon", f"resolved_{stage.name}.txt")
                
                if stage.name == "shuffledns" and not skip:
                    resolvers_file = os.path.join(self.context.config.project_root, "resolvers.txt")
                    if os.path.exists(resolvers_file):
                        context_vars["RESOLVERS"] = resolvers_file
                    else:
                        skip_reason = "resolvers.txt not found."
                        skip = True
                        
            elif stage.name == "httpx":
                context_vars["INPUT"] = self.context.output.resolve_output_path(target, "recon", "resolved.txt")
                context_vars["OUTPUT"] = self.context.output.resolve_output_path(target, "recon", "alive.json")
                
            elif stage.name == "katana":
                context_vars["INPUT"] = self.context.output.resolve_output_path(target, "recon", "alive.txt")
                context_vars["OUTPUT"] = self.context.output.resolve_output_path(target, "recon", "katana_urls.txt")
                
            elif stage.name in ["gau", "waybackurls"]:
                context_vars["OUTPUT"] = self.context.output.resolve_output_path(target, "recon", f"{stage.name}_urls.txt")
                
            elif stage.name == "uro":
                context_vars["INPUT"] = self.context.output.resolve_output_path(target, "recon", "all_urls.txt")
                context_vars["OUTPUT"] = self.context.output.resolve_output_path(target, "recon", "clean_urls.txt")
                
            elif stage.name.startswith("unfurl"):
                context_vars["INPUT"] = self.context.output.resolve_output_path(target, "recon", "clean_urls.txt")
                mode = stage.name.split("_")[1] # domains, paths, parameters
                context_vars["MODE"] = mode
                context_vars["OUTPUT"] = self.context.output.resolve_output_path(target, "recon", f"{mode}.txt")
                context_vars["CAT"] = "type" if platform.system() == "Windows" else "cat"


            # ---------------------------------------------------------
            # 2. Checkpoint Aggregation Engine (Dependency Driven)
            # ---------------------------------------------------------
            input_file = context_vars.get("INPUT", "")
            if input_file:
                input_basename = os.path.basename(input_file)
                # If this stage relies on an aggregated artifact that hasn't been built yet
                if input_basename in self.AGGREGATION_REGISTRY and input_basename not in self.completed_checkpoints:
                    self._run_checkpoint(target, input_basename)
                    self.completed_checkpoints.add(input_basename)
                
                # Check input file existence dynamically
                if not os.path.exists(input_file) or os.path.getsize(input_file) == 0:
                    skip_reason = "Input file is empty or missing."
                    skip = True


            # ---------------------------------------------------------
            # 3. Stage Execution
            # ---------------------------------------------------------
            if skip:
                self.context.events.publish(StageSkipped(
                    workflow_name=workflow.name,
                    stage_name=stage.name,
                    reason=skip_reason
                ))
                self.stats["skipped"] += 1
                self.stats["stages_skipped"].append(stage.name)
                continue

            # Execute via Engine
            self.stats["executed"] += 1
            result = self.engine.execute_stage(workflow.name, stage, context_vars)
            
            if result is None:
                self.stats["skipped"] += 1
                self.stats["stages_skipped"].append(stage.name)
                self.stats["executed"] -= 1 # Adjust since it didn't actually run
                continue
                
            if result.timed_out:
                self.stats["timed_out"] += 1
                self.stats["stages_timed_out"].append(stage.name)
                
                # Check for partial outputs dynamically
                out_file = context_vars.get("OUTPUT", "")
                partial_count = self._get_line_count(out_file) if out_file and os.path.exists(out_file) else 0
                
                self.console.print("\n[bold yellow]" + "-" * 40 + "[/bold yellow]")
                self.console.print(f"[bold yellow]Running {stage.name}...[/bold yellow]")
                self.console.print(f"[yellow]Timeout:[/yellow] {stage.timeout or 'Unknown'} seconds")
                self.console.print(f"[yellow]Elapsed:[/yellow] {self.context.timer.format_time(result.duration)}")
                self.console.print("[yellow]Status:[/yellow] [bold yellow]TIMEOUT[/bold yellow]")
                self.console.print("[yellow]Graceful Termination:[/yellow] SUCCESS")
                self.console.print(f"[yellow]Partial Output:[/yellow] {partial_count} entries preserved")
                self.console.print("[yellow]Workflow continuing...[/yellow]")
                self.console.print("[bold yellow]" + "-" * 40 + "[/bold yellow]\n")

            elif result.success:
                self.stats["successful"] += 1
                self.stats["stages_successful"].append(stage.name)
            else:
                self.stats["failed"] += 1
                self.stats["stages_failed"].append(stage.name)
                
                # Print explicit diagnostics
                self.console.print(f"[bold red]FAILED[/bold red]")
                self.console.print(f"Tool Name: {stage.name}")
                self.console.print(f"Exit Code: {result.exit_code}")
                reason = result.stderr.strip().splitlines()[0] if result.stderr and result.stderr.strip() else "Unknown failure"
                self.console.print(f"Reason:\n{reason}")
                
            if os.path.exists(context_vars.get("OUTPUT", "")):
                self.stats["files_generated"] += 1

            # ---------------------------------------------------------
            # 4. Stage-Specific Parser Normalizations (Not Aggregation)
            # ---------------------------------------------------------
            if stage.name == "amass":
                self._parse_amass_output(target)
            elif stage.name == "dnsx":
                self._parse_dnsx_output(target)
            elif stage.name == "httpx":
                self._process_httpx_output(target)

        # ---------------------------------------------------------
        # End of Pipeline Fallback Checkpoints
        # ---------------------------------------------------------
        # Guarantee all un-triggered aggregations run (e.g. if the workflow ends before hitting a dependency)
        for aggregated_filename in self.AGGREGATION_REGISTRY:
            if aggregated_filename not in self.completed_checkpoints:
                self._run_checkpoint(target, aggregated_filename)
                self.completed_checkpoints.add(aggregated_filename)

        # Generate Intelligence
        self._generate_intelligence(target)

        # Publish Workflow Finished
        self.context.timer.stop()
        runtime = self.context.timer.get_total_runtime()
        self.context.events.publish(WorkflowFinished(workflow_name=workflow.name, total_runtime=runtime))
        
        self.display_summary(workflow.name, workflow.version, target, start_time, datetime.now(), runtime)

    def _run_checkpoint(self, target: str, aggregated_filename: str) -> None:
        """Executes a deterministic checkpoint to generate an aggregated artifact."""
        if aggregated_filename not in self.AGGREGATION_REGISTRY:
            return
            
        inputs = self.AGGREGATION_REGISTRY[aggregated_filename]
        
        # DEBUG: Gather pre-merge counts
        debug_counts = {}
        for f in inputs:
            f_path = self.context.output.resolve_output_path(target, "recon", f)
            debug_counts[f] = self._get_line_count(f_path) if os.path.exists(f_path) else "missing"
            
        self._merge_files(target, inputs, aggregated_filename)
        
        # DEBUG: Gather post-merge count
        out_path = self.context.output.resolve_output_path(target, "recon", aggregated_filename)
        out_count = self._get_line_count(out_path)
        
        # Print Debug Block
        self.console.print("\n[bold cyan]" + "-" * 40 + "[/bold cyan]")
        title = aggregated_filename.replace(".txt", "").replace("_", " ").title()
        self.console.print(f"[bold cyan]{title} Aggregation Checkpoint[/bold cyan]")
        self.console.print("[bold cyan]Input Artifacts:[/bold cyan]")
        for f, count in debug_counts.items():
            val = f"{count} entries" if str(count).isdigit() else count
            self.console.print(f"[cyan]{f:<22} {val}[/cyan]")
            
        self.console.print(f"\n[cyan]Merged & Deduplicated .... {out_count}[/cyan]")
        self.console.print("[cyan]Output file:[/cyan]")
        self.console.print(f"[cyan]{aggregated_filename}[/cyan]")
        self.console.print("[bold cyan]" + "-" * 40 + "[/bold cyan]\n")

    def _normalize_file(self, file_path: str) -> None:
        """Removes blank lines, trims whitespace, deduplicates, and sorts alphabetically."""
        if not os.path.exists(file_path):
            return
            
        clean_lines = set()
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    clean_lines.add(line)
                    
        with open(file_path, "w", encoding="utf-8") as f:
            for item in sorted(clean_lines):
                f.write(item + "\n")

    def _parse_amass_output(self, target: str) -> None:
        """Parses amass output to extract only valid hostnames (e.g. handling FQDN --> domain)."""
        file_path = self.context.output.resolve_output_path(target, "recon", "amass.txt")
        if not os.path.exists(file_path):
            return
            
        valid_domains = set()
        domain_pattern = re.compile(r'^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.replace('-->', ' ').split()
                for part in parts:
                    clean_part = part.strip('()')
                    if domain_pattern.match(clean_part):
                        valid_domains.add(clean_part)
                        break

        with open(file_path, "w", encoding="utf-8") as f:
            for item in sorted(valid_domains):
                f.write(item + "\n")

    def _parse_dnsx_output(self, target: str) -> None:
        """Parses dnsx output by tokenizing and taking the first token, validating it as a hostname."""
        file_path = self.context.output.resolve_output_path(target, "recon", "resolved_dnsx.txt")
        if not os.path.exists(file_path):
            return
            
        valid_domains = set()
        domain_pattern = re.compile(r'^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                tokens = line.split()
                if tokens:
                    candidate = tokens[0].strip()
                    if domain_pattern.match(candidate):
                        valid_domains.add(candidate)

        with open(file_path, "w", encoding="utf-8") as f:
            for item in sorted(valid_domains):
                f.write(item + "\n")

    def _process_httpx_output(self, target: str) -> None:
        """Reads alive.json, extracts URLs to alive.txt."""
        json_path = self.context.output.resolve_output_path(target, "recon", "alive.json")
        txt_path = self.context.output.resolve_output_path(target, "recon", "alive.txt")
        
        if not os.path.exists(json_path):
            return
            
        urls = set()
        with open(json_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    if "url" in data:
                        urls.add(data["url"])
                except json.JSONDecodeError:
                    continue
                    
        with open(txt_path, "w", encoding="utf-8") as f:
            for url in sorted(urls):
                f.write(url + "\n")
                
        if os.path.exists(txt_path):
            self.stats["files_generated"] += 1

    def _merge_files(self, target: str, input_files: list, output_file_name: str) -> None:
        """Normalizes inputs, merges them, removes duplicates, sorts."""
        merged_set = set()
        
        for file_name in input_files:
            file_path = self.context.output.resolve_output_path(target, "recon", file_name)
            if os.path.exists(file_path):
                self._normalize_file(file_path) # Ensure input is normalized
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

    def _get_line_count(self, file_path: str) -> int:
        if not os.path.exists(file_path):
            return 0
        count = 0
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip() and line.strip() != "No results found":
                    count += 1
        return count

    def _generate_intelligence(self, target: str) -> None:
        """Generates intelligence files from normalized output."""
        intel_dir = os.path.join(self.context.output.config.output_dir, target, "recon", "intelligence")
        os.makedirs(intel_dir, exist_ok=True)
        
        def write_intel_file(filename: str, data: list):
            path = os.path.join(intel_dir, filename)
            with open(path, "w", encoding="utf-8") as f:
                if not data:
                    f.write("No results found\n")
                else:
                    for item in data:
                        f.write(item + "\n")
            self.stats["files_generated"] += 1

        # 1. live_hosts.txt
        alive_txt = self.context.output.resolve_output_path(target, "recon", "alive.txt")
        live_hosts = []
        if os.path.exists(alive_txt):
            with open(alive_txt, "r", encoding="utf-8") as f:
                live_hosts = [line.strip() for line in f if line.strip()]
        write_intel_file("live_hosts.txt", live_hosts)
        self.intel_stats["Live Hosts"] = self._get_line_count(os.path.join(intel_dir, "live_hosts.txt"))
        
        # 2. high_value_hosts.txt
        critical_kw = ["admin", "auth", "login", "identity", "sso", "vpn", "gateway", "portal"]
        high_kw = ["api", "dev", "staging", "test", "beta", "internal", "preview"]
        medium_kw = ["www", "blog", "docs", "cdn"]
        
        critical_hosts, high_hosts, medium_hosts = [], [], []
        for host in live_hosts:
            host_lower = host.lower()
            if any(kw in host_lower for kw in critical_kw):
                critical_hosts.append(host)
            elif any(kw in host_lower for kw in high_kw):
                high_hosts.append(host)
            elif any(kw in host_lower for kw in medium_kw):
                medium_hosts.append(host)
                
        high_value = []
        if critical_hosts:
            high_value.append("=== CRITICAL ===")
            high_value.extend(sorted(critical_hosts))
        if high_hosts:
            high_value.append("=== HIGH ===")
            high_value.extend(sorted(high_hosts))
        if medium_hosts:
            high_value.append("=== MEDIUM ===")
            high_value.extend(sorted(medium_hosts))
            
        write_intel_file("high_value_hosts.txt", high_value)
        self.intel_stats["Critical Hosts"] = len(critical_hosts)
        self.intel_stats["High Hosts"] = len(high_hosts)
        self.intel_stats["Medium Hosts"] = len(medium_hosts)

        # Read URLs for URL-based intelligence
        all_urls_path = self.context.output.resolve_output_path(target, "recon", "clean_urls.txt")
        if not os.path.exists(all_urls_path):
            all_urls_path = self.context.output.resolve_output_path(target, "recon", "all_urls.txt")
            
        urls = []
        if os.path.exists(all_urls_path):
            with open(all_urls_path, "r", encoding="utf-8") as f:
                urls = [line.strip() for line in f if line.strip()]
                
        # 3. login_pages.txt
        login_kw = ["login", "signin", "auth", "oauth", "sso"]
        login_pages = sorted(list(set([u for u in urls if any(kw in u.lower() for kw in login_kw)])))
        write_intel_file("login_pages.txt", login_pages)
        self.intel_stats["Login Pages"] = self._get_line_count(os.path.join(intel_dir, "login_pages.txt"))
        
        # 4. admin_panels.txt
        admin_kw = ["admin", "dashboard", "manage", "panel", "control"]
        admin_panels = sorted(list(set([u for u in urls if any(kw in u.lower() for kw in admin_kw)])))
        write_intel_file("admin_panels.txt", admin_panels)
        self.intel_stats["Admin Panels"] = self._get_line_count(os.path.join(intel_dir, "admin_panels.txt"))
        
        # 5. api_endpoints.txt
        api_kw = ["/api", "/graphql", "/swagger", "/openapi", "/v1", "/v2"]
        api_endpoints = sorted(list(set([u for u in urls if any(kw in u.lower() for kw in api_kw)])))
        write_intel_file("api_endpoints.txt", api_endpoints)
        self.intel_stats["API Endpoints"] = self._get_line_count(os.path.join(intel_dir, "api_endpoints.txt"))
        
        # 6. javascript_files.txt
        js_files = sorted(list(set([u for u in urls if u.split('?')[0].endswith('.js')])))
        write_intel_file("javascript_files.txt", js_files)
        self.intel_stats["JavaScript Files"] = self._get_line_count(os.path.join(intel_dir, "javascript_files.txt"))
        
        # 7. interesting_urls.txt
        int_kw = ["/admin", "/login", "/oauth", "/api", "/upload", "/download", "/export", "/import", "/profile", "/settings", "/debug", "/graphql", "/swagger", "/openapi"]
        int_urls = sorted(list(set([u for u in urls if any(kw in u.lower() for kw in int_kw)])))
        write_intel_file("interesting_urls.txt", int_urls)
        
        # 8. interesting_parameters.txt
        params_path = self.context.output.resolve_output_path(target, "recon", "parameters.txt")
        params = set()
        if os.path.exists(params_path):
            with open(params_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip() and line.strip() != "No results found":
                        params.add(line.strip().lower())
                        
        high_param_kw = ["redirect", "url", "next", "return", "callback", "dest", "destination", "continue", "path", "file", "filepath", "download", "upload", "token", "jwt", "access_token", "id_token", "session", "role", "permission", "userid", "id"]
        med_param_kw = ["lang", "page", "sort", "filter", "limit", "offset"]
        
        high_params, med_params = [], []
        for p in params:
            if p in high_param_kw:
                high_params.append(p)
            elif p in med_param_kw:
                med_params.append(p)
                
        interesting_params = []
        if high_params:
            interesting_params.append("=== HIGHEST PRIORITY ===")
            interesting_params.extend(sorted(high_params))
        if med_params:
            interesting_params.append("=== MEDIUM PRIORITY ===")
            interesting_params.extend(sorted(med_params))
            
        write_intel_file("interesting_parameters.txt", interesting_params)
        self.intel_stats["Interesting Parameters"] = len(high_params) + len(med_params)
        
        # 9. technologies.txt
        json_path = self.context.output.resolve_output_path(target, "recon", "alive.json")
        tech_summary = []
        if os.path.exists(json_path):
            with open(json_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        url = data.get("url", "")
                        if not url: continue
                        status = data.get("status_code", "")
                        title = data.get("title", "")
                        webserver = data.get("webserver", "")
                        techs = data.get("tech", [])
                        
                        tech_line = f"[{status}] {url}"
                        if title: tech_line += f" | Title: {title}"
                        if webserver: tech_line += f" | Server: {webserver}"
                        if techs: tech_line += f" | Tech: {', '.join(techs)}"
                        
                        # Deduplicate technology lines to prevent exact duplicates 
                        # But preserve host-specific info (the url is unique per line anyway)
                        if tech_line not in tech_summary:
                            tech_summary.append(tech_line)
                    except json.JSONDecodeError:
                        continue
                        
        write_intel_file("technologies.txt", sorted(tech_summary))
        
        # Gather remaining stats from disk
        self.intel_stats["Subdomains Discovered"] = self._get_line_count(self.context.output.resolve_output_path(target, "recon", "subdomains.txt"))
        self.intel_stats["Resolved Hosts"] = self._get_line_count(self.context.output.resolve_output_path(target, "recon", "resolved.txt"))
        self.intel_stats["Historical URLs"] = self._get_line_count(self.context.output.resolve_output_path(target, "recon", "all_urls.txt"))
        self.intel_stats["Clean URLs"] = self._get_line_count(self.context.output.resolve_output_path(target, "recon", "clean_urls.txt"))

    def display_summary(self, workflow_name: str, version: str, target: str, start: datetime, end: datetime, runtime: float) -> None:
        """Displays the final execution and reconnaissance summaries."""
        self.console.print("\n")
        
        # Execution Summary Table
        exec_table = Table(title="Workflow Execution Summary", show_header=False)
        exec_table.add_column("Metric", style="cyan")
        exec_table.add_column("Value", style="magenta")
        
        exec_table.add_row("Workflow", workflow_name)
        exec_table.add_row("Version", version)
        exec_table.add_row("Target", target)
        exec_table.add_row("Started", start.strftime('%Y-%m-%d %H:%M:%S'))
        exec_table.add_row("Finished", end.strftime('%Y-%m-%d %H:%M:%S'))
        exec_table.add_row("Total Runtime", self.context.timer.format_time(runtime))
        exec_table.add_row("Files Generated", str(self.stats["files_generated"]))
        abs_output_dir = os.path.abspath(self.context.output.create_workflow_dir(target, "recon"))
        exec_table.add_row("Output Directory", abs_output_dir)
        
        self.console.print(exec_table)
        self.console.print("\n")
        
        # Stages Breakdown
        if self.stats['stages_successful']:
            self.console.print(f"[bold green]Successful Stages ({len(self.stats['stages_successful'])})[/bold green]")
            for s in self.stats['stages_successful']:
                self.console.print(f"  [green]✓[/green] {s}")
            
        if self.stats['stages_failed']:
            self.console.print(f"\n[bold red]Failed Stages ({len(self.stats['stages_failed'])})[/bold red]")
            for s in self.stats['stages_failed']:
                self.console.print(f"  [red]✗[/red] {s}")
                
        if self.stats['stages_skipped']:
            self.console.print(f"\n[bold yellow]Skipped Stages ({len(self.stats['stages_skipped'])})[/bold yellow]")
            for s in self.stats['stages_skipped']:
                self.console.print(f"  [yellow]⚠[/yellow] {s}")
                
        if self.stats['stages_timed_out']:
            self.console.print(f"\n[bold yellow]Timed Out Stages ({len(self.stats['stages_timed_out'])})[/bold yellow]")
            for s in self.stats['stages_timed_out']:
                self.console.print(f"  [yellow]![/yellow] {s} (Partial output preserved)")
                
        self.console.print("\n")
        
        # Reconnaissance Summary Table
        recon_table = Table(title="Reconnaissance Summary", show_header=False)
        recon_table.add_column("Metric", style="cyan")
        recon_table.add_column("Count", style="magenta")
        
        recon_table.add_row("Subdomains Discovered", str(self.intel_stats.get("Subdomains Discovered", 0)))
        recon_table.add_row("Resolved Hosts", str(self.intel_stats.get("Resolved Hosts", 0)))
        recon_table.add_row("Live Hosts", str(self.intel_stats.get("Live Hosts", 0)))
        recon_table.add_row("High Value Hosts", "")
        recon_table.add_row("  Critical", str(self.intel_stats.get("Critical Hosts", 0)))
        recon_table.add_row("  High", str(self.intel_stats.get("High Hosts", 0)))
        recon_table.add_row("  Medium", str(self.intel_stats.get("Medium Hosts", 0)))
        recon_table.add_row("Historical URLs", str(self.intel_stats.get("Historical URLs", 0)))
        recon_table.add_row("Clean URLs", str(self.intel_stats.get("Clean URLs", 0)))
        recon_table.add_row("JavaScript Files", str(self.intel_stats.get("JavaScript Files", 0)))
        recon_table.add_row("API Endpoints", str(self.intel_stats.get("API Endpoints", 0)))
        recon_table.add_row("Login Pages", str(self.intel_stats.get("Login Pages", 0)))
        recon_table.add_row("Admin Panels", str(self.intel_stats.get("Admin Panels", 0)))
        recon_table.add_row("Interesting Parameters", str(self.intel_stats.get("Interesting Parameters", 0)))
        
        self.console.print(recon_table)
        self.console.print("\n")
