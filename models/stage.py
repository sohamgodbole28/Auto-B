"""Stage model."""

from dataclasses import dataclass

@dataclass
class Stage:
    """Represents a single step/stage in a workflow."""
    name: str
    tool_name: str
