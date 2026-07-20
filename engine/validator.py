"""
Validator module for verifying schemas and dependencies.
"""

from typing import Dict
import shutil

from core.exceptions import WorkflowException, ToolNotFoundException
from models.tool import Tool
from models.workflow import Workflow

class Validator:
    """Validates workflows and tools before execution."""

    def validate_tools(self, tools: Dict[str, Tool]) -> None:
        """Validates tool schema and checks for duplicates."""
        seen_names = set()
        for tool_name, tool in tools.items():
            if not tool.name:
                raise ToolNotFoundException(f"Tool missing name attribute.")
            if not tool.command_template:
                raise ToolNotFoundException(f"Tool {tool.name} missing command template.")
                
            if tool.name in seen_names:
                raise ToolNotFoundException(f"Duplicate tool name found: {tool.name}")
            seen_names.add(tool.name)

    def validate_workflow(self, workflow: Workflow, available_tools: Dict[str, Tool]) -> None:
        """
        Validates workflow schema, duplicate stages.
        Missing executables will log a warning so the Pipeline can skip them.
        """
        if not workflow.name:
            raise WorkflowException("Workflow is missing 'name'.")
        if not workflow.steps:
            raise WorkflowException(f"Workflow '{workflow.name}' has no steps defined.")
            
        seen_stages = set()
        for stage in workflow.steps:
            if not stage.name:
                raise WorkflowException("Stage in workflow is missing 'name'.")
            if not stage.tool_name:
                raise WorkflowException(f"Stage '{stage.name}' is missing 'tool' reference.")
                
            if stage.name in seen_stages:
                raise WorkflowException(f"Duplicate stage name found in workflow: {stage.name}")
            seen_stages.add(stage.name)
            
            if stage.tool_name not in available_tools:
                raise ToolNotFoundException(f"Stage '{stage.name}' requires tool '{stage.tool_name}' which is not defined in tools.")
