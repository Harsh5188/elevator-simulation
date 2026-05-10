from enum import Enum


class ElevatorStatus(Enum):
    IDLE = 'idle'
    MOVING_UP = 'moving_up'
    MOVING_DOWN = 'moving_down'
    OUT_OF_SERVICE = 'out_of_service'
    RECOVERING = 'recovering'


class PassengerStatus(Enum):
    WAITING = 'waiting'
    ASSIGNED = 'assigned'
    ONBOARD = 'onboard'
    DELIVERED = 'delivered'
    INTERRUPTED = 'interrupted'
