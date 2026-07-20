"""
Application Context module.
"""

from core.config import ConfigManager
from core.output_manager import OutputManager
from core.events import EventBus
from core.logger import AutoBLogger, get_logger
from core.executor import Executor
from core.timer import Timer
from core.environment import EnvironmentValidator

class AppContext:
    """Central dependency container for the application."""

    def __init__(self) -> None:
        self.config = ConfigManager()
        self.output = OutputManager(self.config)
        self.events = EventBus()
        self.logger: AutoBLogger = get_logger(self.output, self.events)
        self.executor = Executor()
        self.timer = Timer()
        self.environment = EnvironmentValidator()
