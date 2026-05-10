from dataclasses import dataclass, field
from typing import List, Optional
from models.enums import ElevatorStatus
from models.journey import PassengerJourney


@dataclass
class Elevator:
    elevator_id: str
    capacity: int
    current_floor: int = 1
    status: ElevatorStatus = ElevatorStatus.IDLE
    onboard: List[PassengerJourney] = field(default_factory=list)
    assigned: List[PassengerJourney] = field(default_factory=list)

    @property
    def available_capacity(self) -> int:
        return self.capacity - len(self.onboard) - len(self.assigned)

    @property
    def projected_stops(self) -> List[int]:
        stops = set()
        for p in self.onboard:
            stops.add(p.request.destination)
        for p in self.assigned:
            stops.add(p.request.source)
        return sorted(stops)

    @property
    def is_active(self) -> bool:
        return self.status != ElevatorStatus.OUT_OF_SERVICE

    @property
    def next_target(self) -> Optional[int]:
        stops = self.projected_stops
        if not stops:
            return None
        if self.status == ElevatorStatus.MOVING_UP:
            above = [s for s in stops if s > self.current_floor]
            if above:
                return min(above)
            below = [s for s in stops if s < self.current_floor]
            return max(below) if below else None
        if self.status == ElevatorStatus.MOVING_DOWN:
            below = [s for s in stops if s < self.current_floor]
            if below:
                return max(below)
            above = [s for s in stops if s > self.current_floor]
            return min(above) if above else None
        other = [s for s in stops if s != self.current_floor]
        return min(other, key=lambda s: abs(s - self.current_floor)) if other else None
