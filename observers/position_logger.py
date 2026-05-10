import csv
import os
from observers.base import SimulationObserver


class PositionLogger(SimulationObserver):
    def __init__(self, output_path: str = 'output/elevator_positions.csv'):
        self._path = output_path
        self._file = None
        self._writer = None
        self._headers_written = False

    def on_tick(self, tick, elevators, journeys):
        if not self._headers_written:
            os.makedirs(os.path.dirname(self._path), exist_ok=True)
            self._file = open(self._path, 'w', newline='')
            headers = ['tick']
            for e in elevators:
                headers.append(e.elevator_id)
            for e in elevators:
                headers.append(f'{e.elevator_id}_status')
            self._writer = csv.DictWriter(self._file, fieldnames=headers)
            self._writer.writeheader()
            self._headers_written = True

        row = {'tick': tick}
        for e in elevators:
            row[e.elevator_id] = e.current_floor
            row[f'{e.elevator_id}_status'] = e.status.value
        self._writer.writerow(row)
        self._file.flush()

    def close(self):
        if self._file:
            self._file.close()
