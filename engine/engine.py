"""
Core Workflow Engine.
"""

import shutil
from typing import Dict, Optional

from core.context import AppContext
from core.exceptions import ExecutionException, WorkflowException
from core.events import (
    WorkflowStarted,
    StageStarted,
    StageFinished,
    StageSkipped,
    WorkflowFinished,
    WorkflowFailed
)
from engine.loader import Loader
from engine.validator import Validator
from models.workflow import Workflow
from models.stage import Stage
from models.stage_result import StageResult
from models.tool import Tool

class Engine:
    """Orchestrates the execution of workflows and stages."""

    def __init__(self, context: AppContext) -> None:
        self.context = context
        self.loader = Loader(
            tools_dir=self.context.output.config.tools_dir,
            workflows_dir=self.context.output.config.workflows_dir
        )
        self.validator = Validator()

    def get_workflow(self, workflow_name: str) -> Workflow:
        """Loads and validates a workflow, returning the object for orchestration."""
        workflow = self.loader.load_workflow(workflow_name)
        tools = self.loader.load_tools()
        self.validator.validate_tools(tools)
        self.validator.validate_workflow(workflow, tools)
        return workflow

    def get_tool(self, tool_name: str) -> Tool:
        """Loads a single tool by name."""
        tools = self.loader.load_tools()
        return tools[tool_name]

    def execute_stage(self, workflow_name: str, stage: Stage, context_vars: Dict[str, str]) -> Optional[StageResult]:
        """
        Executes a single workflow stage using runtime variables.
        Immediately before execution, resolves placeholders in the command template.
        """
        tool = self.get_tool(stage.tool_name)
        executable = tool.executable or tool.name
        
        if not shutil.which(executable):
            self.context.logger.log_warning(f"Tool not installed: {executable}. Skipping stage {stage.name}.")
            self.context.events.publish(StageSkipped(
                workflow_name=workflow_name,
                stage_name=stage.name,
                reason=f"Tool {executable} missing"
            ))
            return None
            
        self.context.events.publish(StageStarted(
            workflow_name=workflow_name,
            stage_name=stage.name
        ))
        
        # Resolve placeholders
        command = tool.command_template
        for key, value in context_vars.items():
            command = command.replace(f"{{{key}}}", str(value))
            
        self.context.logger.log_info(f"Executing: {command}")
            
        # Execute command using the Executor
        result = self.context.executor.execute_command(
            stage_name=stage.name,
            command=command
        )
        
        import os
        empty_output = False
        output_file = context_vars.get("OUTPUT")
        if result.success and output_file and os.path.exists(output_file) and os.path.getsize(output_file) == 0:
            empty_output = True
            self.context.logger.log_warning(f"Stage {stage.name} produced an empty output file: {output_file}")
            
        # Publish result
        self.context.events.publish(StageFinished(
            workflow_name=workflow_name,
            stage_name=stage.name,
            duration=result.duration,
            success=result.success,
            stdout=result.stdout,
            stderr=result.stderr,
            empty_output=empty_output
        ))
        
        return result
