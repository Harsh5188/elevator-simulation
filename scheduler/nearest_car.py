from typing import List, Optional
from models.request import Request
from models.elevator import Elevator
from scheduler.base import SchedulerStrategy


class NearestCarScheduler(SchedulerStrategy):
    def assign(self, request: Request, elevators: List[Elevator]) -> Optional[Elevator]:
        eligible = [e for e in elevators if e.is_active and e.available_capacity > 0]
        if not eligible:
            return None
        return min(eligible, key=lambda e: abs(e.current_floor - request.source))
