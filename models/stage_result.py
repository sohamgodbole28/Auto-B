"""Stage result model."""

from dataclasses import dataclass
from datetime import datetime

@dataclass
class StageResult:
    """Stores the result of executing a command."""
    stage_name: str
    command: str
    exit_code: int
    success: bool
    stdout: str
    stderr: str
    duration: float
    timestamp: datetime
