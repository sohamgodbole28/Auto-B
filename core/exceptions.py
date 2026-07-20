"""
Custom exceptions for Auto-B.
"""

class AutoBException(Exception):
    """Base exception for all Auto-B errors."""
    pass

class ExecutionException(AutoBException):
    """Raised when an execution fails unexpectedly."""
    pass

class WorkflowException(AutoBException):
    """Raised when there is an issue with workflow structure or logic."""
    pass

class ToolNotFoundException(AutoBException):
    """Raised when a required tool is missing."""
    pass

class ConfigurationException(AutoBException):
    """Raised when there is a configuration error."""
    pass
