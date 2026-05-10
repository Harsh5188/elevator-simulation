from abc import ABC, abstractmethod
from typing import List, Optional
from models.request import Request
from models.elevator import Elevator


class SchedulerStrategy(ABC):
    @abstractmethod
    def assign(self, request: Request, elevators: List[Elevator]) -> Optional[Elevator]:
        ...
