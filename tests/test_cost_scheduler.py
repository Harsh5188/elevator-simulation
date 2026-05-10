import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.elevator import Elevator
from models.enums import ElevatorStatus
from models.request import Request
from scheduler.cost_based import CostBasedScheduler, estimate_wait, direction_bonus


def test_estimate_wait_idle():
    e = Elevator(elevator_id='E1', capacity=5, current_floor=3, status=ElevatorStatus.IDLE)
    assert estimate_wait(e, 8, 0) == 5
    assert estimate_wait(e, 1, 0) == 2


def test_estimate_wait_moving():
    e = Elevator(elevator_id='E1', capacity=5, current_floor=3, status=ElevatorStatus.MOVING_UP)
    from models.journey import PassengerJourney
    req = Request(passenger_id='p1', source=7, destination=10, timestamp=0)
    j = PassengerJourney(request=req)
    j.assigned_elevator_id = 'E1'
    from models.enums import PassengerStatus
    j.status = PassengerStatus.ASSIGNED
    e.assigned.append(j)
    wait = estimate_wait(e, 7, 0)
    assert wait == 4, f'Expected 4, got {wait}'


def test_direction_bonus_up():
    e = Elevator(elevator_id='E1', capacity=5, current_floor=3, status=ElevatorStatus.MOVING_UP)
    req = Request(passenger_id='p1', source=5, destination=10, timestamp=0)
    assert direction_bonus(e, req) == -5.0


def test_direction_bonus_no_match():
    e = Elevator(elevator_id='E1', capacity=5, current_floor=8, status=ElevatorStatus.MOVING_UP)
    req = Request(passenger_id='p1', source=5, destination=10, timestamp=0)
    assert direction_bonus(e, req) == 0.0


def test_cost_scheduler_picks_closest():
    sched = CostBasedScheduler()
    e1 = Elevator(elevator_id='E1', capacity=5, current_floor=1)
    e2 = Elevator(elevator_id='E2', capacity=5, current_floor=10)
    req = Request(passenger_id='p1', source=2, destination=8, timestamp=0)
    chosen = sched.assign(req, [e1, e2], current_tick=0)
    assert chosen.elevator_id == 'E1'


def test_cost_scheduler_skips_full():
    sched = CostBasedScheduler()
    from models.journey import PassengerJourney
    e1 = Elevator(elevator_id='E1', capacity=1, current_floor=1)
    dummy_req = Request(passenger_id='x', source=1, destination=5, timestamp=0)
    e1.onboard.append(PassengerJourney(request=dummy_req))
    e2 = Elevator(elevator_id='E2', capacity=5, current_floor=10)
    req = Request(passenger_id='p1', source=2, destination=8, timestamp=0)
    chosen = sched.assign(req, [e1, e2], current_tick=0)
    assert chosen.elevator_id == 'E2'


if __name__ == '__main__':
    test_estimate_wait_idle()
    test_estimate_wait_moving()
    test_direction_bonus_up()
    test_direction_bonus_no_match()
    test_cost_scheduler_picks_closest()
    test_cost_scheduler_skips_full()
    print('All cost scheduler tests passed.')
