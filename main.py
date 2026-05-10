import argparse
import csv
import datetime
import os
import sys

from config import BuildingConfig
from engine.failure import CSVFailurePolicy, FailureEvent, NoFailurePolicy
from engine.simulation import SimulationEngine
from models.request import Request
from observers.metrics import MetricsCollector
from observers.position_logger import PositionLogger
from output.reporter import (
    format_summary,
    print_comparison_table,
    print_summary,
    write_compare_passenger_summary,
    write_compare_summary_txt,
    write_elevator_positions,
    write_passenger_summary,
    write_summary_txt,
)
from scheduler.cost_based import CostBasedScheduler
from scheduler.nearest_car import NearestCarScheduler
from scheduler.round_robin import RoundRobinScheduler

SCHEDULERS = {
    'cost': CostBasedScheduler,
    'nearest': NearestCarScheduler,
    'roundrobin': RoundRobinScheduler,
}

BASE_OUTPUT = 'RunOutput'


def _make_run_dir(filename_stem: str, algo_name: str) -> str:
    ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    path = os.path.join(BASE_OUTPUT, filename_stem, algo_name, ts)
    os.makedirs(path, exist_ok=True)
    return path


def load_requests(path: str, num_floors: int) -> list:
    requests = []
    seen_ids: set = set()
    with open(path, newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            ts = int(row['time'])
            src = int(row['source'])
            dst = int(row['dest'])
            pid = row['id'].strip()
            if not pid:
                print('WARNING: Rejecting row - passenger id is empty', file=sys.stderr)
                continue
            if pid in seen_ids:
                print(f'WARNING: Rejecting {pid} - duplicate passenger id', file=sys.stderr)
                continue
            if ts < 0:
                print(f'WARNING: Rejecting {pid} - negative timestamp', file=sys.stderr)
                continue
            if src < 1 or src > num_floors or dst < 1 or dst > num_floors:
                print(f'WARNING: Rejecting {pid} - floor out of range', file=sys.stderr)
                continue
            if src == dst:
                print(f'WARNING: Rejecting {pid} - source == destination', file=sys.stderr)
                continue
            seen_ids.add(pid)
            requests.append(Request(passenger_id=pid, source=src, destination=dst, timestamp=ts))
    return requests


def load_failures(path: str) -> list:
    events = []
    with open(path, newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            events.append(FailureEvent(
                tick=int(row['tick']),
                elevator_id=row['elevator_id'].strip(),
                event=row['event'].strip(),
            ))
    return events


def run_single(requests, failures, config, scheduler_name, filename_stem):
    output_dir = _make_run_dir(filename_stem, scheduler_name)

    pos_logger = PositionLogger(os.path.join(output_dir, 'elevator_positions.csv'))
    metrics = MetricsCollector()
    engine = SimulationEngine(config)
    engine.add_observer(pos_logger)
    engine.add_observer(metrics)
    result = engine.run(requests, failures)
    pos_logger.close()

    write_passenger_summary(result, output_dir)
    write_summary_txt(result, scheduler_name, output_dir)
    print_summary(result, scheduler_name)
    print(f'\nOutput written to: {output_dir}')
    return result


def run_compare(requests, failures, num_floors, num_elevators, capacity, filename_stem):
    output_dir = _make_run_dir(filename_stem, 'compare')

    metrics_results = {}
    sim_results = {}

    for name, cls in SCHEDULERS.items():
        config = BuildingConfig(
            num_floors=num_floors,
            num_elevators=num_elevators,
            capacity=capacity,
            scheduler=cls(),
            failure_policy=NoFailurePolicy(),
        )
        engine = SimulationEngine(config)
        result = engine.run(requests, failures)
        metrics_results[name] = format_summary(result)
        sim_results[name] = result

    print_comparison_table(metrics_results)
    write_compare_passenger_summary(sim_results, output_dir)
    write_compare_summary_txt(metrics_results, output_dir)
    for name, result in sim_results.items():
        write_elevator_positions(result, name, output_dir)

    print(f'\nOutput written to: {output_dir}')
    return metrics_results


def main():
    parser = argparse.ArgumentParser(description='KKR Elevator Simulation')
    parser.add_argument('--requests', required=True, help='Path to requests CSV')
    parser.add_argument('--failures', default=None, help='Path to failures CSV')
    parser.add_argument('--floors', type=int, default=60)
    parser.add_argument('--elevators', type=int, default=3,
                        help='Number of elevators (1-10)')
    parser.add_argument('--capacity', type=int, default=8)
    parser.add_argument('--scheduler', default='cost', choices=list(SCHEDULERS.keys()))
    parser.add_argument('--compare', action='store_true')
    args = parser.parse_args()

    if not (1 <= args.elevators <= 10):
        parser.error(f'--elevators must be between 1 and 10, got {args.elevators}')

    filename_stem = os.path.splitext(os.path.basename(args.requests))[0]
    requests = load_requests(args.requests, args.floors)
    failures = load_failures(args.failures) if args.failures else []

    if args.compare:
        run_compare(requests, failures, args.floors, args.elevators, args.capacity, filename_stem)
    else:
        config = BuildingConfig(
            num_floors=args.floors,
            num_elevators=args.elevators,
            capacity=args.capacity,
            scheduler=SCHEDULERS[args.scheduler](),
            failure_policy=NoFailurePolicy(),
        )
        config.validate()
        run_single(requests, failures, config, args.scheduler, filename_stem)


if __name__ == '__main__':
    main()
