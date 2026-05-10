from abc import ABC


class SimulationObserver(ABC):
    def on_tick(self, tick, elevators, journeys): pass
    def on_pickup(self, tick, elevator, journey): pass
    def on_dropoff(self, tick, elevator, journey): pass
    def on_failure(self, tick, elevator): pass
    def on_recovery(self, tick, elevator): pass
