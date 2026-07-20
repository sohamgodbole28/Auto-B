"""Stage model."""

from dataclasses import dataclass
from typing import Optional

@dataclass
class Stage:
    """Represents a single step/stage in a workflow."""
    name: str
    tool_name: str
    timeout: Optional[int] = None
