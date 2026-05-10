import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import BuildingConfig
from engine.simulation import SimulationEngine
from models.request import Request
from models.enums import PassengerStatus
from scheduler.cost_based import CostBasedScheduler


def make_engine(num_floors, num_elevators, capacity, scheduler=None):
    config = BuildingConfig(
        num_floors=num_floors,
        num_elevators=num_elevators,
        capacity=capacity,
        scheduler=scheduler or CostBasedScheduler(),
    )
    return SimulationEngine(config)


def test1_single_elevator_single_passenger():
    """Test 1: Single elevator at floor 1, passenger goes 1->5."""
    engine = make_engine(10, 1, 5)
    requests = [Request(passenger_id='passenger1', source=1, destination=5, timestamp=0)]
    result = engine.run(requests)

    j = result.journeys['passenger1']
    assert j.pickup_tick == 0, f'Expected pickup_tick=0, got {j.pickup_tick}'
    assert j.dropoff_tick == 4, f'Expected dropoff_tick=4, got {j.dropoff_tick}'
    assert j.wait_time == 0, f'Expected wait_time=0, got {j.wait_time}'
    assert j.travel_time == 4, f'Expected travel_time=4, got {j.travel_time}'
    assert j.total_time == 4, f'Expected total_time=4, got {j.total_time}'
    assert j.status == PassengerStatus.DELIVERED
    print('TEST 1 PASSED: single elevator, single passenger')


def test2_two_passengers_different_elevators():
    """Test 2: Two passengers same floor, should be split across 2 elevators."""
    engine = make_engine(20, 2, 5)
    requests = [
        Request(passenger_id='passenger1', source=1, destination=10, timestamp=0),
        Request(passenger_id='passenger2', source=1, destination=20, timestamp=0),
    ]
    result = engine.run(requests)

    j1 = result.journeys['passenger1']
    j2 = result.journeys['passenger2']
    assert j1.assigned_elevator_id != j2.assigned_elevator_id, (
        f'Expected different elevators, both got {j1.assigned_elevator_id}'
    )
    assert j1.status == PassengerStatus.DELIVERED
    assert j2.status == PassengerStatus.DELIVERED
    print('TEST 2 PASSED: two passengers assigned to different elevators')


def test3_elevator_at_capacity():
    """Test 3: Capacity=1, second passenger waits until first is delivered."""
    engine = make_engine(10, 1, 1)
    requests = [
        Request(passenger_id='passenger1', source=1, destination=10, timestamp=0),
        Request(passenger_id='passenger2', source=1, destination=5, timestamp=0),
    ]
    result = engine.run(requests)

    j1 = result.journeys['passenger1']
    j2 = result.journeys['passenger2']

    assert j1.status == PassengerStatus.DELIVERED
    assert j2.status == PassengerStatus.DELIVERED
    assert j1.pickup_tick == 0, f'passenger1 pickup_tick expected 0, got {j1.pickup_tick}'
    # passenger2 must board only after passenger1 is delivered (dropoff at tick 9)
    assert j2.pickup_tick > j1.dropoff_tick, (
        f'passenger2 pickup ({j2.pickup_tick}) must be after passenger1 dropoff ({j1.dropoff_tick})'
    )
    print(f'TEST 3 PASSED: capacity enforced - p2 pickup at {j2.pickup_tick} after p1 dropoff at {j1.dropoff_tick}')


def test4_elevator_failure_mid_ride():
    """Test 4: E1 fails at tick 5 while carrying passenger1 from floor 1 to 20."""
    from engine.failure import FailureEvent
    engine = make_engine(20, 2, 5)
    requests = [Request(passenger_id='passenger1', source=1, destination=20, timestamp=0)]
    failures = [FailureEvent(tick=5, elevator_id='E1', event='fail')]
    result = engine.run(requests, failures)

    # The original journey should be INTERRUPTED
    j_orig = result.journeys.get('passenger1')
    assert j_orig is not None
    assert j_orig.status == PassengerStatus.INTERRUPTED, f'Expected INTERRUPTED, got {j_orig.status}'

    # A re-request journey should exist with _R suffix
    rerequested = [pid for pid in result.journeys if pid.startswith('passenger1_R')]
    assert len(rerequested) >= 1, 'Expected a re-request journey to exist'

    # The re-requested journey should eventually be DELIVERED
    j_r = result.journeys[rerequested[0]]
    assert j_r.status == PassengerStatus.DELIVERED, f'Re-request not delivered: {j_r.status}'
    assert j_r.request.source == 6, f'Expected safe_floor=6, got {j_r.request.source}'
    assert j_r.request.destination == 20
    assert j_r.reassign_count >= 1
    print(f'TEST 4 PASSED: failure at tick 5, passenger re-queued from floor 6, eventually delivered')


if __name__ == '__main__':
    test1_single_elevator_single_passenger()
    test2_two_passengers_different_elevators()
    test3_elevator_at_capacity()
    test4_elevator_failure_mid_ride()
    print('\nAll tests passed.')
