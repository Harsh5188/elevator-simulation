from typing import List, Optional
from models.request import Request
from models.elevator import Elevator
from scheduler.base import SchedulerStrategy


class RoundRobinScheduler(SchedulerStrategy):
    def __init__(self):
        self._index = 0

    def assign(self, request: Request, elevators: List[Elevator]) -> Optional[Elevator]:
        eligible = [e for e in elevators if e.is_active and e.available_capacity > 0]
        if not eligible:
            return None
        elevator = eligible[self._index % len(eligible)]
        self._index += 1
        return elevator
