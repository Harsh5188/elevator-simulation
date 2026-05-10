import csv
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List
from models.elevator import Elevator


@dataclass(frozen=True)
class FailureEvent:
    tick: int
    elevator_id: str
    event: str


class FailurePolicy(ABC):
    @abstractmethod
    def get_events(self, tick: int, elevators: List[Elevator]) -> List[FailureEvent]:
        ...


class NoFailurePolicy(FailurePolicy):
    def get_events(self, tick: int, elevators: List[Elevator]) -> List[FailureEvent]:
        return []


class CSVFailurePolicy(FailurePolicy):
    def __init__(self, events: List[FailureEvent]):
        self._map: dict = {}
        for e in events:
            self._map.setdefault(e.tick, []).append(e)

    def get_events(self, tick: int, elevators: List[Elevator]) -> List[FailureEvent]:
        return self._map.get(tick, [])

    @classmethod
    def from_csv(cls, path: str) -> 'CSVFailurePolicy':
        events = []
        with open(path, newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                events.append(FailureEvent(
                    tick=int(row['tick']),
                    elevator_id=row['elevator_id'].strip(),
                    event=row['event'].strip(),
                ))
        return cls(events)
