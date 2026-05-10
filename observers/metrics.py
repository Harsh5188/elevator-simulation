import statistics
from typing import Dict, List
from models.journey import PassengerJourney
from models.enums import PassengerStatus
from observers.base import SimulationObserver


class MetricsCollector(SimulationObserver):
    def __init__(self):
        self.pickups: List[dict] = []
        self.dropoffs: List[dict] = []
        self.failures: List[dict] = []
        self.recoveries: List[dict] = []

    def on_pickup(self, tick, elevator, journey):
        self.pickups.append({'tick': tick, 'elevator': elevator.elevator_id,
                             'passenger': journey.request.passenger_id})

    def on_dropoff(self, tick, elevator, journey):
        self.dropoffs.append({'tick': tick, 'elevator': elevator.elevator_id,
                              'passenger': journey.request.passenger_id})

    def on_failure(self, tick, elevator):
        self.failures.append({'tick': tick, 'elevator': elevator.elevator_id})

    def on_recovery(self, tick, elevator):
        self.recoveries.append({'tick': tick, 'elevator': elevator.elevator_id})

    def compute(self, journeys: Dict[str, PassengerJourney]) -> dict:
        delivered = [j for j in journeys.values()
                     if j.status == PassengerStatus.DELIVERED and j.wait_time is not None]

        if not delivered:
            return {
                'total_passengers': 0,
                'min_wait_time': None, 'max_wait_time': None, 'avg_wait_time': None,
                'min_total_time': None, 'max_total_time': None, 'avg_total_time': None,
                'p95_wait_time': None, 'p95_total_time': None,
                'reassigned_count': 0,
            }

        wait_times = [j.wait_time for j in delivered]
        total_times = [j.total_time for j in delivered]
        reassigned = sum(1 for j in journeys.values() if j.reassign_count > 0)

        def p95(vals):
            sorted_vals = sorted(vals)
            idx = int(len(sorted_vals) * 0.95)
            return sorted_vals[min(idx, len(sorted_vals) - 1)]

        return {
            'total_passengers': len(delivered),
            'min_wait_time': min(wait_times),
            'max_wait_time': max(wait_times),
            'avg_wait_time': statistics.mean(wait_times),
            'min_total_time': min(total_times),
            'max_total_time': max(total_times),
            'avg_total_time': statistics.mean(total_times),
            'p95_wait_time': p95(wait_times),
            'p95_total_time': p95(total_times),
            'reassigned_count': reassigned,
        }
