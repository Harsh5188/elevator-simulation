import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import BuildingConfig
from engine.simulation import SimulationEngine
from models.enums import PassengerStatus
from models.request import Request
from scheduler.cost_based import CostBasedScheduler


def make_engine(num_floors=20, num_elevators=2, capacity=5):
    config = BuildingConfig(
        num_floors=num_floors, num_elevators=num_elevators,
        capacity=capacity, scheduler=CostBasedScheduler()
    )
    return SimulationEngine(config)


def test_source_equals_destination_ignored():
    engine = make_engine()
    good = Request(passenger_id='p1', source=1, destination=5, timestamp=0)
    bad = Request(passenger_id='bad', source=3, destination=3, timestamp=0)
    result = engine.run([good, bad])
    assert 'bad' not in result.journeys
    assert result.journeys['p1'].status == PassengerStatus.DELIVERED
    print('test_source_equals_destination_ignored PASSED')


def test_all_elevators_full_request_waits():
    engine = make_engine(num_elevators=1, capacity=1)
    r1 = Request(passenger_id='p1', source=1, destination=10, timestamp=0)
    r2 = Request(passenger_id='p2', source=1, destination=5, timestamp=0)
    result = engine.run([r1, r2])
    j1 = result.journeys['p1']
    j2 = result.journeys['p2']
    assert j1.status == PassengerStatus.DELIVERED
    assert j2.status == PassengerStatus.DELIVERED
    assert j2.pickup_tick > j1.dropoff_tick
    print('test_all_elevators_full_request_waits PASSED')


def test_multiple_requests_same_timestamp():
    engine = make_engine(num_elevators=3)
    requests = [
        Request(passenger_id=f'p{i}', source=1, destination=5+i, timestamp=0)
        for i in range(3)
    ]
    result = engine.run(requests)
    for i in range(3):
        assert result.journeys[f'p{i}'].status == PassengerStatus.DELIVERED
    print('test_multiple_requests_same_timestamp PASSED')


def test_timestamps_with_gap():
    engine = make_engine()
    r1 = Request(passenger_id='p1', source=1, destination=3, timestamp=0)
    r2 = Request(passenger_id='p2', source=5, destination=10, timestamp=100)
    result = engine.run([r1, r2])
    assert result.journeys['p1'].status == PassengerStatus.DELIVERED
    assert result.journeys['p2'].status == PassengerStatus.DELIVERED
    print('test_timestamps_with_gap PASSED')


if __name__ == '__main__':
    test_source_equals_destination_ignored()
    test_all_elevators_full_request_waits()
    test_multiple_requests_same_timestamp()
    test_timestamps_with_gap()
    print('All edge case tests passed.')
