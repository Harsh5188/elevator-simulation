from dataclasses import dataclass, field
from scheduler.base import SchedulerStrategy
from scheduler.cost_based import CostBasedScheduler
from engine.failure import FailurePolicy, NoFailurePolicy


@dataclass
class BuildingConfig:
    num_floors: int
    num_elevators: int
    capacity: int
    scheduler: SchedulerStrategy = field(default_factory=CostBasedScheduler)
    failure_policy: FailurePolicy = field(default_factory=NoFailurePolicy)

    def validate(self):
        assert self.num_floors >= 2, 'Need at least 2 floors'
        assert 1 <= self.num_elevators <= 10, 'Number of elevators must be between 1 and 10'
        assert self.capacity >= 1, 'Capacity must be positive'
