"""
Timer module for measuring execution times.
"""

import time
from typing import Optional

class Timer:
    """Measures execution time of stages and total runtime."""

    def __init__(self) -> None:
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.stage_start_times: dict[str, float] = {}
        self.stage_durations: dict[str, float] = {}

    def start(self) -> None:
        """Starts the total runtime timer."""
        self.start_time = time.time()

    def stop(self) -> None:
        """Stops the total runtime timer."""
        self.end_time = time.time()

    def get_total_runtime(self) -> float:
        """Returns the total runtime in seconds."""
        if self.start_time is None:
            return 0.0
        end = self.end_time if self.end_time is not None else time.time()
        return end - self.start_time

    def start_stage(self, stage_name: str) -> None:
        """Starts a timer for a specific stage."""
        self.stage_start_times[stage_name] = time.time()

    def stop_stage(self, stage_name: str) -> float:
        """Stops the timer for a specific stage and returns the duration."""
        if stage_name not in self.stage_start_times:
            return 0.0
        duration = time.time() - self.stage_start_times[stage_name]
        self.stage_durations[stage_name] = duration
        return duration

    def get_stage_duration(self, stage_name: str) -> float:
        """Returns the recorded duration of a stage."""
        return self.stage_durations.get(stage_name, 0.0)

    def format_time(self, seconds: float) -> str:
        """Formats seconds into a human-readable string."""
        mins, secs = divmod(seconds, 60)
        hours, mins = divmod(mins, 60)
        if hours > 0:
            return f"{int(hours)}h {int(mins)}m {secs:.2f}s"
        if mins > 0:
            return f"{int(mins)}m {secs:.2f}s"
        return f"{secs:.2f}s"
