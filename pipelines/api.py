"""
API Pipeline.
"""

from engine.engine import Engine

class ApiPipeline:
    """Coordinator for the API Workflow."""

    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def execute(self) -> None:
        """Prepares, executes, and post-processes the API workflow."""
        target = "example.com"
        self.engine.execute_workflow_by_name("api")
