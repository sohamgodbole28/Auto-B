"""
Configuration module.
"""

import os
import yaml
from typing import Any, Dict

class ConfigManager:
    """Centrally manages configuration settings for Auto-B."""

    def __init__(self, config_path: str = "config.yaml") -> None:
        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.config_path = os.path.join(self.project_root, config_path)
        self.config_data: Dict[str, Any] = {}
        
        # Default settings
        self.output_dir: str = os.path.join(self.project_root, "output")
        self.log_dir: str = os.path.join(self.project_root, "logs")
        self.temp_dir: str = os.path.join(self.project_root, "temp")
        self.tools_dir: str = os.path.join(self.project_root, "tools")
        self.workflows_dir: str = os.path.join(self.project_root, "workflows")
        
        self.thread_count: int = 10
        self.timeout: int = 3600
        self.verbosity: str = "info"
        self.color_mode: bool = True
        
        self.load_config()

    def load_config(self) -> None:
        """Loads configuration from a YAML file if it exists."""
        if not os.path.exists(self.config_path):
            return
            
        with open(self.config_path, "r", encoding="utf-8") as f:
            try:
                self.config_data = yaml.safe_load(f) or {}
                self._apply_config()
            except yaml.YAMLError:
                self.config_data = {}

    def _apply_config(self) -> None:
        """Applies loaded YAML data to attributes."""
        self.output_dir = self.config_data.get("output_dir", self.output_dir)
        self.log_dir = self.config_data.get("log_dir", self.log_dir)
        self.temp_dir = self.config_data.get("temp_dir", self.temp_dir)
        self.tools_dir = self.config_data.get("tools_dir", self.tools_dir)
        self.workflows_dir = self.config_data.get("workflows_dir", self.workflows_dir)
        self.thread_count = self.config_data.get("thread_count", self.thread_count)
        self.timeout = self.config_data.get("timeout", self.timeout)
        self.verbosity = self.config_data.get("verbosity", self.verbosity)
        self.color_mode = self.config_data.get("color_mode", self.color_mode)
