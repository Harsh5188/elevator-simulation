from dataclasses import dataclass


@dataclass(frozen=True)
class Request:
    passenger_id: str
    source: int
    destination: int
    timestamp: int
