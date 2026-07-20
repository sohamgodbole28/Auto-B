"""
Executor module for running individual commands.
"""

import subprocess
from datetime import datetime

from core.timer import Timer
from models.stage_result import StageResult

class Executor:
    """Executes isolated subprocess commands."""

    def __init__(self) -> None:
        self.timer = Timer()

    def execute_command(self, stage_name: str, command: str, shell: bool = True) -> StageResult:
        """
        Runs a subprocess command.
        
        Args:
            stage_name (str): The name of the stage being executed.
            command (str): The command to run.
            shell (bool): Whether to run via shell.
            
        Returns:
            StageResult: The result of the execution containing status and outputs.
        """
        timestamp = datetime.now()
        self.timer.start_stage("command_exec")
        
        try:
            process = subprocess.run(
                command,
                shell=shell,
                capture_output=True,
                text=True,
                check=False
            )
            success = process.returncode == 0
            exit_code = process.returncode
            stdout = process.stdout
            stderr = process.stderr
        except Exception as e:
            success = False
            exit_code = -1
            stdout = ""
            stderr = str(e)
            
        duration = self.timer.stop_stage("command_exec")
        
        return StageResult(
            stage_name=stage_name,
            command=command,
            exit_code=exit_code,
            success=success,
            stdout=stdout,
            stderr=stderr,
            duration=duration,
            timestamp=timestamp
        )
