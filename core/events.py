"""
Event Bus module.
"""

from dataclasses import dataclass
from typing import Callable, Dict, List, Type

@dataclass(frozen=True)
class Event:
    pass

@dataclass(frozen=True)
class WorkflowStarted(Event):
    workflow_name: str

@dataclass(frozen=True)
class StageStarted(Event):
    workflow_name: str
    stage_name: str

@dataclass(frozen=True)
class StageFinished(Event):
    workflow_name: str
    stage_name: str
    duration: float
    success: bool
    stdout: str
    stderr: str
    empty_output: bool = False

@dataclass(frozen=True)
class StageSkipped(Event):
    workflow_name: str
    stage_name: str
    reason: str

@dataclass(frozen=True)
class WorkflowFinished(Event):
    workflow_name: str
    total_runtime: float

@dataclass(frozen=True)
class WorkflowFailed(Event):
    workflow_name: str
    reason: str


class EventBus:
    """Lightweight internal event bus for pub/sub operations."""
    
    def __init__(self) -> None:
        self._subscribers: Dict[Type[Event], List[Callable[[Event], None]]] = {}

    def subscribe(self, event_type: Type[Event], callback: Callable[[Event], None]) -> None:
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)

    def unsubscribe(self, event_type: Type[Event], callback: Callable[[Event], None]) -> None:
        if event_type in self._subscribers:
            try:
                self._subscribers[event_type].remove(callback)
            except ValueError:
                pass

    def publish(self, event: Event) -> None:
        event_type = type(event)
        
        if event_type in self._subscribers:
            for callback in self._subscribers[event_type]:
                callback(event)
                
        for base in event_type.__bases__:
            if issubclass(base, Event) and base in self._subscribers:
                for callback in self._subscribers[base]:
                    callback(event)
