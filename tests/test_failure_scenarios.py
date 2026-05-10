import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import BuildingConfig
from engine.failure import FailureEvent
from engine.simulation import SimulationEngine
from models.enums import ElevatorStatus, PassengerStatus
from models.request import Request
from scheduler.cost_based import CostBasedScheduler


def make_engine(num_floors=20, num_elevators=2, capacity=5):
    config = BuildingConfig(
        num_floors=num_floors, num_elevators=num_elevators,
        capacity=capacity, scheduler=CostBasedScheduler()
    )
    return SimulationEngine(config)


def test_fail_idle_elevator():
    engine = make_engine()
    failures = [FailureEvent(tick=0, elevator_id='E2', event='fail')]
    requests = [Request(passenger_id='p1', source=1, destination=5, timestamp=0)]
    result = engine.run(requests, failures)
    e2 = next(e for e in engine.elevators if e.elevator_id == 'E2')
    assert e2.status == ElevatorStatus.OUT_OF_SERVICE
    j = result.journeys['p1']
    assert j.status == PassengerStatus.DELIVERED
    print('test_fail_idle_elevator PASSED')


def test_fail_mid_ride_requeues():
    engine = make_engine()
    requests = [Request(passenger_id='p1', source=1, destination=20, timestamp=0)]
    failures = [FailureEvent(tick=5, elevator_id='E1', event='fail')]
    result = engine.run(requests, failures)

    j_orig = result.journeys['p1']
    assert j_orig.status == PassengerStatus.INTERRUPTED

    rerequests = [pid for pid in result.journeys if 'p1_R' in pid]
    assert len(rerequests) >= 1
    j_r = result.journeys[rerequests[0]]
    assert j_r.status == PassengerStatus.DELIVERED
    assert j_r.request.source == 6
    print('test_fail_mid_ride_requeues PASSED')


def test_recover_after_fail():
    engine = make_engine(num_elevators=1, num_floors=10)
    requests = [Request(passenger_id='p1', source=1, destination=5, timestamp=20)]
    failures = [
        FailureEvent(tick=0, elevator_id='E1', event='fail'),
        FailureEvent(tick=10, elevator_id='E1', event='recover'),
    ]
    result = engine.run(requests, failures)
    j = result.journeys['p1']
    assert j.status == PassengerStatus.DELIVERED
    print('test_recover_after_fail PASSED')


def test_fail_with_assigned_passengers():
    engine = make_engine(num_elevators=2)
    requests = [Request(passenger_id='p1', source=5, destination=10, timestamp=0)]
    failures = [FailureEvent(tick=1, elevator_id='E1', event='fail')]
    result = engine.run(requests, failures)
    j = result.journeys['p1']
    assert j.status == PassengerStatus.DELIVERED
    print('test_fail_with_assigned_passengers PASSED')


if __name__ == '__main__':
    test_fail_idle_elevator()
    test_fail_mid_ride_requeues()
    test_recover_after_fail()
    test_fail_with_assigned_passengers()
    print('All failure scenario tests passed.')
