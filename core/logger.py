"""
Logger module for writing logs and recording stage outputs.
"""

import logging
from datetime import datetime
from typing import Optional

from core.output_manager import OutputManager
from core.events import (
    EventBus,
    Event,
    WorkflowStarted,
    StageStarted,
    StageFinished,
    WorkflowFinished,
    WorkflowFailed
)

class AutoBLogger:
    """Handles writing logs and recording stdout/stderr as a singleton."""
    
    _instance: Optional['AutoBLogger'] = None

    def __new__(cls, output_manager: Optional[OutputManager] = None, event_bus: Optional[EventBus] = None) -> 'AutoBLogger':
        if cls._instance is None:
            if output_manager is None or event_bus is None:
                raise ValueError("Logger must be initialized with OutputManager and EventBus.")
            cls._instance = super(AutoBLogger, cls).__new__(cls)
            cls._instance._initialize(output_manager, event_bus)
        return cls._instance

    def _initialize(self, output_manager: OutputManager, event_bus: EventBus) -> None:
        self.output = output_manager
        
        log_file = self.output.resolve_log_path(filename=f"autob_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        
        self.logger = logging.getLogger("AutoB")
        self.logger.setLevel(logging.DEBUG)
        
        if not self.logger.handlers:
            fh = logging.FileHandler(log_file, encoding="utf-8")
            fh.setLevel(logging.DEBUG)
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            fh.setFormatter(formatter)
            self.logger.addHandler(fh)
            
        # Subscribe to workflow lifecycle events
        event_bus.subscribe(WorkflowStarted, self._on_workflow_started)
        event_bus.subscribe(StageStarted, self._on_stage_started)
        event_bus.subscribe(StageFinished, self._on_stage_finished)
        event_bus.subscribe(WorkflowFinished, self._on_workflow_finished)
        event_bus.subscribe(WorkflowFailed, self._on_workflow_failed)

    def log_info(self, message: str) -> None:
        """Logs an informational message."""
        self.logger.info(message)

    def log_error(self, message: str) -> None:
        """Logs an error message."""
        self.logger.error(message)
        
    def log_warning(self, message: str) -> None:
        """Logs a warning message."""
        self.logger.warning(message)

    def log_debug(self, message: str) -> None:
        """Logs a debug message."""
        self.logger.debug(message)

    def log_critical(self, message: str) -> None:
        """Logs a critical message."""
        self.logger.critical(message)

    # Event Handlers

    def _on_workflow_started(self, event: WorkflowStarted) -> None:
        self.log_info(f"Workflow Started: {event.workflow_name}")

    def _on_stage_started(self, event: StageStarted) -> None:
        self.log_info(f"Stage Started: {event.stage_name}")

    def _on_stage_finished(self, event: StageFinished) -> None:
        timestamp = datetime.now().isoformat()
        
        log_content = (
            f"=== STAGE: {event.stage_name} ===\n"
            f"Timestamp: {timestamp}\n"
            f"--- STDOUT ---\n{event.stdout}\n"
            f"--- STDERR ---\n{event.stderr}\n"
            f"====================\n"
        )
        
        # We can put stage logs inside the global log dir for now or target dir.
        stage_file = self.output.resolve_log_path(
            filename=f"stage_{event.stage_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        )
        with open(stage_file, "w", encoding="utf-8") as f:
            f.write(log_content)
            
        if event.success:
            self.log_info(f"Stage Finished: {event.stage_name} (Duration: {event.duration:.2f}s)")
        else:
            self.log_error(f"Stage Failed: {event.stage_name} (Duration: {event.duration:.2f}s)")

    def _on_workflow_finished(self, event: WorkflowFinished) -> None:
        self.log_info(f"Workflow Finished: {event.workflow_name} (Total Runtime: {event.total_runtime:.2f}s)")

    def _on_workflow_failed(self, event: WorkflowFailed) -> None:
        self.log_error(f"Workflow Failed: {event.workflow_name}. Reason: {event.reason}")

def get_logger(output_manager: Optional[OutputManager] = None, event_bus: Optional[EventBus] = None) -> AutoBLogger:
    """Returns the singleton logger instance."""
    return AutoBLogger(output_manager, event_bus)
