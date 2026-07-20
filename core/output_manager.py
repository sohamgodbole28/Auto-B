"""
Output Manager module.
"""

import os
import shutil
from typing import Optional

from core.config import ConfigManager

class OutputManager:
    """Single authority for all filesystem operations in Auto-B."""

    def __init__(self, config: ConfigManager) -> None:
        self.config = config
        self._initialize_core_directories()

    def _initialize_core_directories(self) -> None:
        """Ensures that base required directories exist."""
        os.makedirs(self.config.output_dir, exist_ok=True)
        os.makedirs(self.config.log_dir, exist_ok=True)
        os.makedirs(self.config.temp_dir, exist_ok=True)
        os.makedirs(self.config.tools_dir, exist_ok=True)
        os.makedirs(self.config.workflows_dir, exist_ok=True)

    def create_target_dir(self, target: str) -> str:
        """Creates and returns the output directory for a specific target."""
        target_dir = os.path.join(self.config.output_dir, target)
        os.makedirs(target_dir, exist_ok=True)
        return target_dir

    def create_workflow_dir(self, target: str, workflow_name: str) -> str:
        """Creates and returns the directory for a workflow under a target."""
        target_dir = self.create_target_dir(target)
        workflow_dir = os.path.join(target_dir, workflow_name)
        os.makedirs(workflow_dir, exist_ok=True)
        return workflow_dir

    def create_temp_dir(self) -> str:
        """Creates and returns the temp directory."""
        os.makedirs(self.config.temp_dir, exist_ok=True)
        return self.config.temp_dir

    def resolve_output_path(self, target: str, workflow_name: str, filename: str) -> str:
        """Resolves an absolute path for a workflow output file."""
        workflow_dir = self.create_workflow_dir(target, workflow_name)
        return os.path.join(workflow_dir, filename)

    def resolve_log_path(self, target: Optional[str] = None, filename: str = "run.log") -> str:
        """Resolves an absolute path for a log file."""
        if target:
            target_dir = self.create_target_dir(target)
            log_dir = os.path.join(target_dir, "logs")
            os.makedirs(log_dir, exist_ok=True)
            return os.path.join(log_dir, filename)
        
        # Global log dir
        os.makedirs(self.config.log_dir, exist_ok=True)
        return os.path.join(self.config.log_dir, filename)

    def clean_temp(self) -> None:
        """Cleans all temporary files."""
        if os.path.exists(self.config.temp_dir):
            for filename in os.listdir(self.config.temp_dir):
                file_path = os.path.join(self.config.temp_dir, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                except Exception:
                    pass

    def archive_run(self, target: str) -> None:
        """Archives a completed run for a target (Not implemented fully yet)."""
        pass

    def verify_directory_existence(self, path: str) -> bool:
        """Verifies if a directory exists."""
        return os.path.isdir(path)
