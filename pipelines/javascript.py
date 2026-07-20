"""
JavaScript Pipeline.
"""

from engine.engine import Engine

class JavaScriptPipeline:
    """Coordinator for the JavaScript Workflow."""

    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def execute(self) -> None:
        """Prepares, executes, and post-processes the javascript workflow."""
        target = "example.com"
        self.engine.execute_workflow_by_name("javascript")
