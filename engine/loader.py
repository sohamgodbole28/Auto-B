"""
YAML parsing and loading module.
"""

import os
import yaml
from typing import Dict, List

from core.exceptions import ConfigurationException, WorkflowException
from models.tool import Tool
from models.workflow import Workflow
from models.stage import Stage

class Loader:
    """Loads and parses YAML definitions into typed models."""
    
    def __init__(self, tools_dir: str, workflows_dir: str) -> None:
        self.tools_dir = tools_dir
        self.workflows_dir = workflows_dir

    def load_tools(self) -> Dict[str, Tool]:
        """Loads all tool definitions from the tools directory."""
        tools: Dict[str, Tool] = {}
        
        if not os.path.exists(self.tools_dir):
            return tools
            
        for filename in os.listdir(self.tools_dir):
            if filename.endswith(".yaml") or filename.endswith(".yml"):
                filepath = os.path.join(self.tools_dir, filename)
                with open(filepath, "r", encoding="utf-8") as f:
                    try:
                        data = yaml.safe_load(f) or {}
                        # Convert dict to Tool model
                        tool = Tool(
                            name=data.get("name", ""),
                            description=data.get("description", ""),
                            executable=data.get("executable", ""),
                            command_template=data.get("command_template", data.get("command", "")),
                            output=data.get("output", ""),
                            required_tools=data.get("required", [])
                        )
                        tools[tool.name] = tool
                    except Exception as e:
                        raise ConfigurationException(f"Failed to load tool {filename}: {str(e)}")
                        
        return tools

    def load_workflow(self, workflow_name: str) -> Workflow:
        """Loads a specific workflow by name."""
        filename = f"{workflow_name}.yaml"
        filepath = os.path.join(self.workflows_dir, filename)
        
        if not os.path.exists(filepath):
            raise WorkflowException(f"Workflow file {filename} not found in {self.workflows_dir}")
            
        with open(filepath, "r", encoding="utf-8") as f:
            try:
                data = yaml.safe_load(f) or {}
                
                stages = []
                for step_data in data.get("steps", []):
                    # Step can be a dict with name and tool
                    stages.append(Stage(
                        name=step_data.get("name", ""),
                        tool_name=step_data.get("tool", "")
                    ))
                    
                workflow = Workflow(
                    name=data.get("name", ""),
                    description=data.get("description", ""),
                    author=data.get("author", ""),
                    version=str(data.get("version", "")),
                    estimated_runtime=data.get("estimated_runtime", ""),
                    required_tools=data.get("required_tools", []),
                    steps=stages
                )
                return workflow
            except Exception as e:
                raise WorkflowException(f"Failed to load workflow {filename}: {str(e)}")
