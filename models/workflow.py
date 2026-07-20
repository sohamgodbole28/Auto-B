"""Workflow model."""

from dataclasses import dataclass
from typing import List
from models.stage import Stage

@dataclass
class Workflow:
    """Represents an entire automated workflow."""
    name: str
    description: str
    author: str
    version: str
    estimated_runtime: str
    required_tools: List[str]
    steps: List[Stage]
    output_directory: str = ""
