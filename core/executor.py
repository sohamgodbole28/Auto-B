"""
Executor module for running individual commands.
"""

import subprocess
import time
from typing import Optional
from datetime import datetime

from core.timer import Timer
from models.stage_result import StageResult

class Executor:
    """Executes isolated subprocess commands."""

    def __init__(self) -> None:
        self.timer = Timer()

    def execute_command(self, stage_name: str, command: str, shell: bool = True, timeout: Optional[int] = None) -> StageResult:
        """
        Runs a subprocess command with graceful timeout support.
        
        Args:
            stage_name (str): The name of the stage being executed.
            command (str): The command to run.
            shell (bool): Whether to run via shell.
            timeout (int, optional): The maximum execution time in seconds.
            
        Returns:
            StageResult: The result of the execution containing status and outputs.
        """
        timestamp = datetime.now()
        self.timer.start_stage("command_exec")
        
        success = False
        timed_out = False
        exit_code = -1
        stdout = ""
        stderr = ""
        
        try:
            process = subprocess.Popen(
                command,
                shell=shell,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            try:
                stdout, stderr = process.communicate(timeout=timeout)
                exit_code = process.returncode
                success = exit_code == 0
            except subprocess.TimeoutExpired as e:
                timed_out = True
                success = False
                
                # 1. Graceful termination
                process.terminate()
                
                # 2. Wait up to 3 seconds for it to flush buffers and exit cleanly
                try:
                    stdout, stderr = process.communicate(timeout=3)
                except subprocess.TimeoutExpired:
                    # 3. Force kill if it refused to exit
                    process.kill()
                    stdout, stderr = process.communicate()
                
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
            timed_out=timed_out,
            stdout=stdout or "",
            stderr=stderr or "",
            duration=duration,
            timestamp=timestamp
        )
