from dataclasses import dataclass, field
from typing import Optional
from models.enums import PassengerStatus
from models.request import Request


@dataclass
class PassengerJourney:
    request: Request
    status: PassengerStatus = PassengerStatus.WAITING
    assigned_elevator_id: Optional[str] = None
    pickup_tick: Optional[int] = None
    dropoff_tick: Optional[int] = None
    reassign_count: int = 0

    @property
    def wait_time(self) -> Optional[int]:
        if self.pickup_tick is None:
            return None
        return self.pickup_tick - self.request.timestamp

    @property
    def travel_time(self) -> Optional[int]:
        if self.pickup_tick is None or self.dropoff_tick is None:
            return None
        return self.dropoff_tick - self.pickup_tick

    @property
    def total_time(self) -> Optional[int]:
        if self.dropoff_tick is None:
            return None
        return self.dropoff_tick - self.request.timestamp
