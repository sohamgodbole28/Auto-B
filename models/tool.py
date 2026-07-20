"""Tool model."""

from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Tool:
    """Represents a single executable tool definition."""
    name: str
    description: str
    executable: str
    command_template: str
    output: str
    required_tools: List[str]
