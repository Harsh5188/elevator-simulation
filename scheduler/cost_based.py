from typing import List, Optional
from models.request import Request
from models.elevator import Elevator
from models.enums import ElevatorStatus
from scheduler.base import SchedulerStrategy


def estimate_wait(elevator: Elevator, target_floor: int, current_tick: int) -> int:
    if elevator.status == ElevatorStatus.IDLE:
        return abs(elevator.current_floor - target_floor)
    stops = elevator.projected_stops
    if not stops:
        return abs(elevator.current_floor - target_floor)
    ticks = 0
    pos = elevator.current_floor
    for stop in stops:
        ticks += abs(stop - pos)
        pos = stop
        if stop == target_floor:
            return ticks
    return ticks + abs(pos - target_floor)


def direction_bonus(elevator: Elevator, request: Request) -> float:
    if elevator.status == ElevatorStatus.MOVING_UP:
        if elevator.current_floor <= request.source and request.source <= request.destination:
            return -5.0
    if elevator.status == ElevatorStatus.MOVING_DOWN:
        if elevator.current_floor >= request.source and request.source >= request.destination:
            return -5.0
    return 0.0


class CostBasedScheduler(SchedulerStrategy):
    def __init__(self, alpha: float = 1.0, beta: float = 0.8, gamma: float = 0.5):
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma

    def assign(self, request: Request, elevators: List[Elevator],
               current_tick: int = 0) -> Optional[Elevator]:
        eligible = [e for e in elevators if e.is_active and e.available_capacity > 0]
        if not eligible:
            return None

        def cost(elevator: Elevator) -> float:
            wait = estimate_wait(elevator, request.source, current_tick)
            travel = abs(request.source - request.destination)
            delay = self._delay_to_existing(elevator, request)
            fairness = -(current_tick - request.timestamp) * 0.3
            direction = direction_bonus(elevator, request)
            return (self.alpha * wait +
                    self.beta * travel +
                    self.gamma * delay +
                    fairness + direction)

        return min(eligible, key=cost)

    def _delay_to_existing(self, elevator: Elevator, request: Request) -> float:
        total = len(elevator.onboard) + len(elevator.assigned)
        if total == 0:
            return 0.0
        return total * 2.0
