import csv
import os
import statistics
from typing import Dict
from models.journey import PassengerJourney
from models.enums import PassengerStatus


def format_summary(result) -> dict:
    journeys = result.journeys
    delivered = [j for j in journeys.values()
                 if j.status == PassengerStatus.DELIVERED and j.wait_time is not None]

    if not delivered:
        return {
            'total_passengers': 0,
            'min_wait_time': None,
            'avg_wait_time': None,
            'max_wait_time': None,
            'min_total_time': None,
            'avg_total_time': None,
            'max_total_time': None,
            'p95_wait_time': None,
            'p95_total_time': None,
            'reassigned_count': 0,
        }

    wait_times = [j.wait_time for j in delivered]
    total_times = [j.total_time for j in delivered]
    reassigned = sum(1 for j in journeys.values() if j.reassign_count > 0)

    def p95(vals):
        sorted_vals = sorted(vals)
        idx = int(len(sorted_vals) * 0.95)
        return sorted_vals[min(idx, len(sorted_vals) - 1)]

    return {
        'total_passengers': len(delivered),
        'min_wait_time': min(wait_times),
        'avg_wait_time': round(statistics.mean(wait_times), 2),
        'max_wait_time': max(wait_times),
        'min_total_time': min(total_times),
        'avg_total_time': round(statistics.mean(total_times), 2),
        'max_total_time': max(total_times),
        'p95_wait_time': p95(wait_times),
        'p95_total_time': p95(total_times),
        'reassigned_count': reassigned,
    }


def write_passenger_summary(result, output_dir: str = 'RunOutput') -> None:
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, 'passenger_summary.csv')
    fieldnames = [
        'passenger_id', 'source', 'destination', 'request_tick',
        'assigned_elevator', 'pickup_tick', 'dropoff_tick',
        'wait_time', 'travel_time', 'total_time', 'reassign_count',
    ]
    with open(path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for pid, journey in result.journeys.items():
            writer.writerow({
                'passenger_id': pid,
                'source': journey.request.source,
                'destination': journey.request.destination,
                'request_tick': journey.request.timestamp,
                'assigned_elevator': journey.assigned_elevator_id or '',
                'pickup_tick': journey.pickup_tick if journey.pickup_tick is not None else '',
                'dropoff_tick': journey.dropoff_tick if journey.dropoff_tick is not None else '',
                'wait_time': journey.wait_time if journey.wait_time is not None else '',
                'travel_time': journey.travel_time if journey.travel_time is not None else '',
                'total_time': journey.total_time if journey.total_time is not None else '',
                'reassign_count': journey.reassign_count,
            })


def write_elevator_positions(result, scheduler_name: str, output_dir: str) -> None:
    """Write elevator positions from result.position_log (no observer needed)."""
    if not result.position_log:
        return
    os.makedirs(output_dir, exist_ok=True)
    filename = f'{scheduler_name}_elevator_positions.csv'
    path = os.path.join(output_dir, filename)
    fieldnames = list(result.position_log[0].keys())
    with open(path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(result.position_log)


def write_compare_passenger_summary(sim_results: dict, output_dir: str) -> None:
    """
    Write a single merged passenger_summary.csv for a compare run.
    Each row is one passenger. Columns repeat per scheduler:
      passenger_id, source, destination, request_tick,
      {sched}_assigned_elevator, {sched}_pickup_tick, {sched}_dropoff_tick,
      {sched}_wait_time, {sched}_travel_time, {sched}_total_time, {sched}_reassign_count
    """
    os.makedirs(output_dir, exist_ok=True)
    scheduler_names = list(sim_results.keys())

    per_sched_cols = [
        'assigned_elevator', 'pickup_tick', 'dropoff_tick',
        'wait_time', 'travel_time', 'total_time', 'reassign_count',
    ]

    fieldnames = ['passenger_id', 'source', 'destination', 'request_tick']
    for name in scheduler_names:
        for col in per_sched_cols:
            fieldnames.append(f'{name}_{col}')

    # Collect all passenger IDs in a stable order (by first-seen timestamp)
    all_pids = list(dict.fromkeys(
        pid
        for r in sim_results.values()
        for pid in sorted(r.journeys, key=lambda p: r.journeys[p].request.timestamp)
    ))

    path = os.path.join(output_dir, 'passenger_summary.csv')
    with open(path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for pid in all_pids:
            # Base info from first result that has this passenger
            base_journey = next(
                (r.journeys[pid] for r in sim_results.values() if pid in r.journeys), None
            )
            if base_journey is None:
                continue
            row = {
                'passenger_id': pid,
                'source': base_journey.request.source,
                'destination': base_journey.request.destination,
                'request_tick': base_journey.request.timestamp,
            }
            for name in scheduler_names:
                j = sim_results[name].journeys.get(pid)
                if j:
                    row[f'{name}_assigned_elevator'] = j.assigned_elevator_id or ''
                    row[f'{name}_pickup_tick'] = j.pickup_tick if j.pickup_tick is not None else ''
                    row[f'{name}_dropoff_tick'] = j.dropoff_tick if j.dropoff_tick is not None else ''
                    row[f'{name}_wait_time'] = j.wait_time if j.wait_time is not None else ''
                    row[f'{name}_travel_time'] = j.travel_time if j.travel_time is not None else ''
                    row[f'{name}_total_time'] = j.total_time if j.total_time is not None else ''
                    row[f'{name}_reassign_count'] = j.reassign_count
                else:
                    for col in per_sched_cols:
                        row[f'{name}_{col}'] = ''
            writer.writerow(row)


def write_compare_summary_txt(metrics_results: dict, output_dir: str) -> None:
    """Write a side-by-side summary.txt for a compare run."""
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, 'summary.txt')
    with open(path, 'w') as f:
        f.write('SCHEDULER COMPARISON SUMMARY\n')
        f.write('=' * 50 + '\n\n')
        for name, metrics in metrics_results.items():
            f.write(f'Scheduler: {name}\n')
            f.write('-' * 30 + '\n')
            for k, v in metrics.items():
                f.write(f'  {k}: {v}\n')
            f.write('\n')


def print_summary(result, scheduler_name: str = 'cost_based') -> None:
    metrics = format_summary(result)
    print(f'\n{"="*50}')
    print(f'Scheduler: {scheduler_name}')
    print(f'{"="*50}')
    print(f'Total passengers delivered : {metrics["total_passengers"]}')
    print(f'Min wait time              : {metrics["min_wait_time"]}')
    print(f'Avg wait time              : {metrics["avg_wait_time"]}')
    print(f'Max wait time              : {metrics["max_wait_time"]}')
    print(f'Min total time             : {metrics["min_total_time"]}')
    print(f'Avg total time             : {metrics["avg_total_time"]}')
    print(f'Max total time             : {metrics["max_total_time"]}')
    print(f'p95 wait time              : {metrics["p95_wait_time"]}')
    print(f'p95 total time             : {metrics["p95_total_time"]}')
    print(f'Reassigned passengers      : {metrics["reassigned_count"]}')


def print_comparison_table(results: dict) -> None:
    metrics_keys = [
        'total_passengers',
        'min_wait_time', 'avg_wait_time', 'max_wait_time',
        'min_total_time', 'avg_total_time', 'max_total_time',
        'p95_wait_time', 'p95_total_time',
        'reassigned_count',
    ]
    names = list(results.keys())
    col_w = 18

    header = f'{"Metric":<28}' + ''.join(f'{n:>{col_w}}' for n in names)
    print(f'\n{"="*len(header)}')
    print('SCHEDULER COMPARISON')
    print(f'{"="*len(header)}')
    print(header)
    print('-' * len(header))

    for key in metrics_keys:
        row = f'{key:<28}'
        for name in names:
            val = results[name].get(key)
            row += f'{str(val):>{col_w}}'
        print(row)
    print(f'{"="*len(header)}\n')


def write_summary_txt(result, scheduler_name: str, output_dir: str = 'RunOutput') -> None:
    os.makedirs(output_dir, exist_ok=True)
    metrics = format_summary(result)
    path = os.path.join(output_dir, 'summary.txt')
    with open(path, 'w') as f:
        f.write(f'Scheduler: {scheduler_name}\n')
        for k, v in metrics.items():
            f.write(f'{k}: {v}\n')
