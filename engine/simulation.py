import logging
from typing import Dict, List, Optional
from models.elevator import Elevator
from models.enums import ElevatorStatus, PassengerStatus
from models.journey import PassengerJourney
from models.request import Request
from engine.failure import FailureEvent

logger = logging.getLogger(__name__)


class SimulationResult:
    def __init__(self, journeys: Dict[str, PassengerJourney], position_log: List[dict]):
        self.journeys = journeys
        self.position_log = position_log


class SimulationEngine:
    def __init__(self, config):
        self.config = config
        self.scheduler = config.scheduler
        self.elevators: List[Elevator] = [
            Elevator(elevator_id=f'E{i+1}', capacity=config.capacity)
            for i in range(config.num_elevators)
        ]
        self.current_tick: int = 0
        self.journeys: Dict[str, PassengerJourney] = {}
        self.unassigned: List[Request] = []
        self.position_log: List[dict] = []
        self.observers: list = []

    def add_observer(self, observer) -> None:
        self.observers.append(observer)

    def run(self, requests: List[Request],
            failures: List[FailureEvent] = None) -> SimulationResult:
        failures = failures or []
        all_requests = sorted(requests, key=lambda r: r.timestamp)
        failure_map = self._index_failures(failures)
        max_tick = self._compute_max_tick(all_requests)

        while not self._is_complete(all_requests):
            self._tick(all_requests, failure_map)
            self.current_tick += 1
            if self.current_tick > max_tick + 500:
                logger.warning('Safety valve triggered at tick %d', self.current_tick)
                break

        return SimulationResult(self.journeys, self.position_log)

    def _tick(self, all_requests: List[Request], failure_map: dict) -> None:
        self._apply_failures(failure_map.get(self.current_tick, []))
        self._inject_requests(all_requests)
        self._move_elevators()
        self._process_dropoffs()
        self._run_scheduler()
        self._process_pickups()
        self._log_state()
        for obs in self.observers:
            obs.on_tick(self.current_tick, self.elevators, self.journeys)

    def _inject_requests(self, all_requests: List[Request]) -> None:
        for req in all_requests:
            if req.timestamp == self.current_tick:
                if req.source == req.destination:
                    logger.warning('Rejecting request %s: source == destination', req.passenger_id)
                    continue
                if req.passenger_id in self.journeys:
                    logger.warning('Rejecting request %s: duplicate passenger id', req.passenger_id)
                else:
                    self.journeys[req.passenger_id] = PassengerJourney(request=req)
                    self.unassigned.append(req)

    def _move_elevators(self) -> None:
        for elevator in self.elevators:
            if elevator.status == ElevatorStatus.OUT_OF_SERVICE:
                continue
            target = elevator.next_target
            if target is None:
                elevator.status = ElevatorStatus.IDLE
                continue
            if target > elevator.current_floor:
                elevator.current_floor += 1
                elevator.status = ElevatorStatus.MOVING_UP
            elif target < elevator.current_floor:
                elevator.current_floor -= 1
                elevator.status = ElevatorStatus.MOVING_DOWN

    def _process_dropoffs(self) -> None:
        for elevator in self.elevators:
            if not elevator.is_active:
                continue
            arrived = [p for p in elevator.onboard
                       if p.request.destination == elevator.current_floor]
            for journey in arrived:
                elevator.onboard.remove(journey)
                journey.status = PassengerStatus.DELIVERED
                journey.dropoff_tick = self.current_tick
                for obs in self.observers:
                    obs.on_dropoff(self.current_tick, elevator, journey)

    def _process_pickups(self) -> None:
        for elevator in self.elevators:
            if not elevator.is_active:
                continue
            to_board = [p for p in elevator.assigned
                        if p.request.source == elevator.current_floor]
            for journey in to_board:
                if elevator.capacity - len(elevator.onboard) > 0:
                    elevator.assigned.remove(journey)
                    elevator.onboard.append(journey)
                    journey.status = PassengerStatus.ONBOARD
                    journey.pickup_tick = self.current_tick
                    for obs in self.observers:
                        obs.on_pickup(self.current_tick, elevator, journey)

    def _run_scheduler(self) -> None:
        still_unassigned: List[Request] = []
        for req in self.unassigned:
            journey = self.journeys.get(req.passenger_id)
            if journey is None:
                continue
            if journey.status not in (PassengerStatus.WAITING,):
                continue

            if hasattr(self.scheduler, 'assign'):
                import inspect
                sig = inspect.signature(self.scheduler.assign)
                if 'current_tick' in sig.parameters:
                    elevator = self.scheduler.assign(req, self.elevators,
                                                     current_tick=self.current_tick)
                else:
                    elevator = self.scheduler.assign(req, self.elevators)
            else:
                elevator = None

            if elevator is None:
                still_unassigned.append(req)
            else:
                journey.status = PassengerStatus.ASSIGNED
                journey.assigned_elevator_id = elevator.elevator_id
                elevator.assigned.append(journey)
        self.unassigned = still_unassigned

    def _apply_failures(self, events: List[FailureEvent]) -> None:
        for event in events:
            elevator = self._get_elevator(event.elevator_id)
            if not elevator:
                continue

            if event.event == 'fail':
                for obs in self.observers:
                    obs.on_failure(self.current_tick, elevator)

                for journey in elevator.assigned:
                    journey.status = PassengerStatus.WAITING
                    journey.assigned_elevator_id = None
                    journey.reassign_count += 1
                    self.unassigned.append(journey.request)
                elevator.assigned.clear()

                safe_floor = self._safe_floor(elevator)
                for journey in elevator.onboard:
                    journey.dropoff_tick = self.current_tick
                    journey.status = PassengerStatus.INTERRUPTED
                    new_req = Request(
                        passenger_id=journey.request.passenger_id + '_R',
                        source=safe_floor,
                        destination=journey.request.destination,
                        timestamp=self.current_tick,
                    )
                    new_journey = PassengerJourney(request=new_req)
                    new_journey.reassign_count = journey.reassign_count + 1
                    self.journeys[new_req.passenger_id] = new_journey
                    self.unassigned.append(new_req)
                elevator.onboard.clear()
                elevator.current_floor = safe_floor
                elevator.status = ElevatorStatus.OUT_OF_SERVICE

            elif event.event == 'recover':
                elevator.status = ElevatorStatus.IDLE
                for obs in self.observers:
                    obs.on_recovery(self.current_tick, elevator)

    def _safe_floor(self, elevator: Elevator) -> int:
        if elevator.status == ElevatorStatus.MOVING_UP:
            floor = elevator.current_floor + 1
        elif elevator.status == ElevatorStatus.MOVING_DOWN:
            floor = elevator.current_floor - 1
        else:
            floor = elevator.current_floor
        return max(1, min(floor, self.config.num_floors))

    def _log_state(self) -> None:
        entry = {'tick': self.current_tick}
        for e in self.elevators:
            entry[e.elevator_id] = e.current_floor
            entry[f'{e.elevator_id}_status'] = e.status.value
        self.position_log.append(entry)

    def _get_elevator(self, elevator_id: str) -> Optional[Elevator]:
        for e in self.elevators:
            if e.elevator_id == elevator_id:
                return e
        return None

    def _index_failures(self, failures: List[FailureEvent]) -> dict:
        mapping: dict = {}
        for f in failures:
            mapping.setdefault(f.tick, []).append(f)
        return mapping

    def _compute_max_tick(self, all_requests: List[Request]) -> int:
        if not all_requests:
            return 0
        max_ts = max(r.timestamp for r in all_requests)
        max_dist = self.config.num_floors * 2
        return max_ts + max_dist

    def _is_complete(self, all_requests: List[Request]) -> bool:
        if not all_requests:
            return True
        for req in all_requests:
            pid = req.passenger_id
            if pid not in self.journeys:
                return False
            j = self.journeys[pid]
            if j.status not in (PassengerStatus.DELIVERED, PassengerStatus.INTERRUPTED):
                return False
        for pid, journey in self.journeys.items():
            if journey.status not in (PassengerStatus.DELIVERED, PassengerStatus.INTERRUPTED):
                return False
        return True
