import csv
import datetime
import io
import os

from flask import Flask
from flask_restx import Api, Resource, fields, reqparse
from werkzeug.datastructures import FileStorage

from config import BuildingConfig
from engine.failure import FailureEvent, NoFailurePolicy
from engine.simulation import SimulationEngine
from models.request import Request
from output.reporter import (
    format_summary,
    write_compare_passenger_summary,
    write_compare_summary_txt,
    write_elevator_positions,
    write_passenger_summary,
    write_summary_txt,
)
from scheduler.cost_based import CostBasedScheduler
from scheduler.nearest_car import NearestCarScheduler
from scheduler.round_robin import RoundRobinScheduler

app = Flask(__name__)
api = Api(
    app,
    version='1.0',
    title='Elevator System Simulation',
    description='KKR take-home assignment - Harsh Verdhan Shukla',
    doc='/docs',
)

ns = api.namespace('simulate', description='Simulation endpoints')

# ---------------------------------------------------------------------------
# Swagger models
# ---------------------------------------------------------------------------

metrics_model = api.model('Metrics', {
    'total_passengers': fields.Integer(),
    'min_wait_time': fields.Float(),
    'avg_wait_time': fields.Float(),
    'max_wait_time': fields.Float(),
    'min_total_time': fields.Float(),
    'avg_total_time': fields.Float(),
    'max_total_time': fields.Float(),
    'p95_wait_time': fields.Float(),
    'p95_total_time': fields.Float(),
    'reassigned_count': fields.Integer(),
})

upload_response = api.model('UploadResponse', {
    'status':        fields.String(example='completed'),
    'message':       fields.String(),
    'output_dir':    fields.String(description='Folder where output files were written'),
    'rows_parsed':   fields.Integer(description='Passenger rows successfully parsed'),
    'rows_skipped':  fields.Integer(description='Rows skipped due to validation errors'),
    'skip_reasons':  fields.List(fields.String(), description='Per-row reason for each skip'),
    'metrics':       fields.Nested(metrics_model),
})

upload_compare_response = api.model('UploadCompareResponse', {
    'status':       fields.String(),
    'message':      fields.String(),
    'output_dir':   fields.String(description='Folder where output files were written'),
    'rows_parsed':  fields.Integer(),
    'rows_skipped': fields.Integer(),
    'skip_reasons': fields.List(fields.String()),
    'comparison':   fields.Raw(description='Metrics for each scheduler side by side'),
})

# ---------------------------------------------------------------------------
# RequestParsers (makes Swagger UI show form fields for multipart/form-data)
# ---------------------------------------------------------------------------

_upload_parser = reqparse.RequestParser()
_upload_parser.add_argument(
    'file', location='files', type=FileStorage, required=True,
    help='CSV file with columns: time, id, source, dest',
)
_upload_parser.add_argument(
    'failures_file', location='files', type=FileStorage, required=False,
    help='(Optional) CSV file with columns: tick, elevator_id, event',
)
_upload_parser.add_argument(
    'num_floors', location='form', type=int, default=60,
    help='Total number of floors in the building (default: 60)',
)
_upload_parser.add_argument(
    'num_elevators', location='form', type=int, default=3,
    help='Number of elevators, must be 1-10 (default: 3)',
)
_upload_parser.add_argument(
    'capacity', location='form', type=int, default=8,
    help='Maximum passengers per elevator (default: 8)',
)
_upload_parser.add_argument(
    'scheduler', location='form', type=str, default='cost',
    choices=('cost', 'nearest', 'roundrobin'),
    help='Scheduling algorithm: cost | nearest | roundrobin (default: cost)',
)

_upload_compare_parser = reqparse.RequestParser()
_upload_compare_parser.add_argument(
    'file', location='files', type=FileStorage, required=True,
    help='CSV file with columns: time, id, source, dest',
)
_upload_compare_parser.add_argument(
    'failures_file', location='files', type=FileStorage, required=False,
    help='(Optional) CSV file with columns: tick, elevator_id, event',
)
_upload_compare_parser.add_argument(
    'num_floors', location='form', type=int, default=60,
    help='Total number of floors in the building (default: 60)',
)
_upload_compare_parser.add_argument(
    'num_elevators', location='form', type=int, default=3,
    help='Number of elevators, must be 1-10 (default: 3)',
)
_upload_compare_parser.add_argument(
    'capacity', location='form', type=int, default=8,
    help='Maximum passengers per elevator (default: 8)',
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SCHEDULER_MAP = {
    'cost': CostBasedScheduler,
    'nearest': NearestCarScheduler,
    'roundrobin': RoundRobinScheduler,
}

BASE_OUTPUT = 'RunOutput'


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_run_dir(filename_stem: str, algo_name: str) -> str:
    ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    path = os.path.join(BASE_OUTPUT, filename_stem, algo_name, ts)
    os.makedirs(path, exist_ok=True)
    return path


def _parse_csv_stream(stream, num_floors: int):
    """
    Parse a CSV file stream into a list of Request objects.
    Expected columns: time, id, source, dest
    Returns (requests, skipped_count, skip_reasons).
    """
    text = io.TextIOWrapper(stream, encoding='utf-8')
    reader = csv.DictReader(text)

    required = {'time', 'id', 'source', 'dest'}
    if not required.issubset(set(reader.fieldnames or [])):
        raise ValueError(
            f'CSV must have columns: time, id, source, dest. '
            f'Got: {reader.fieldnames}'
        )

    requests, skipped = [], 0
    seen_ids: set = set()
    skip_reasons: list = []

    for row in reader:
        try:
            ts  = int(row['time'])
            src = int(row['source'])
            dst = int(row['dest'])
            pid = row['id'].strip()
        except (ValueError, KeyError):
            skipped += 1
            skip_reasons.append('unparseable row')
            continue

        if not pid:
            skipped += 1
            skip_reasons.append('empty passenger id')
            continue
        if pid in seen_ids:
            skipped += 1
            skip_reasons.append(f'duplicate id: {pid}')
            continue
        if ts < 0:
            skipped += 1
            skip_reasons.append(f'{pid}: negative timestamp')
            continue
        if src < 1 or src > num_floors or dst < 1 or dst > num_floors:
            skipped += 1
            skip_reasons.append(f'{pid}: floor out of range (floors 1-{num_floors})')
            continue
        if src == dst:
            skipped += 1
            skip_reasons.append(f'{pid}: source == destination (floor {src})')
            continue

        seen_ids.add(pid)
        requests.append(Request(passenger_id=pid, source=src, destination=dst, timestamp=ts))

    return requests, skipped, skip_reasons


def _parse_failures_stream(stream) -> list:
    """
    Parse an optional failures CSV stream into a list of FailureEvent objects.
    Expected columns: tick, elevator_id, event
    """
    text = io.TextIOWrapper(stream, encoding='utf-8')
    reader = csv.DictReader(text)

    required = {'tick', 'elevator_id', 'event'}
    if not required.issubset(set(reader.fieldnames or [])):
        raise ValueError(
            f'Failures CSV must have columns: tick, elevator_id, event. '
            f'Got: {reader.fieldnames}'
        )

    events = []
    for row in reader:
        try:
            events.append(FailureEvent(
                tick=int(row['tick']),
                elevator_id=row['elevator_id'].strip(),
                event=row['event'].strip(),
            ))
        except (ValueError, KeyError):
            continue  # skip unparseable rows silently

    return events


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@ns.route('/upload')
class SimulateUpload(Resource):
    @ns.expect(_upload_parser)
    @ns.response(200, 'Success', upload_response)
    @ns.response(400, 'Validation error')
    def post(self):
        '''Upload a CSV file and run the simulation with a chosen scheduler.

        The CSV must have a header row with columns: **time, id, source, dest**

        Example file contents:

            time,id,source,dest
            0,p1,1,51
            0,p2,1,37
            10,p3,20,1

        Output files are written to **RunOutput/{filename}/{scheduler}/{timestamp}/**.
        '''
        args = _upload_parser.parse_args()
        uploaded = args['file']

        if not uploaded.filename.endswith('.csv'):
            api.abort(400, 'Uploaded file must be a .csv')

        num_floors    = args['num_floors']    or 60
        num_elevators = args['num_elevators'] or 3
        capacity      = args['capacity']      or 8
        scheduler_key = args['scheduler']     or 'cost'

        if not (1 <= num_elevators <= 10):
            api.abort(400, f'num_elevators must be between 1 and 10, got {num_elevators}')

        try:
            requests, skipped, skip_reasons = _parse_csv_stream(uploaded.stream, num_floors)
        except ValueError as e:
            api.abort(400, str(e))

        if not requests:
            api.abort(400, f'No valid passenger rows found. '
                          f'Skipped {skipped} rows: {skip_reasons}')

        failures_file = args.get('failures_file')
        if failures_file and not failures_file.filename.endswith('.csv'):
            api.abort(400, 'Failures file must be a .csv')
        try:
            failures = _parse_failures_stream(failures_file.stream) if failures_file else []
        except ValueError as e:
            api.abort(400, str(e))

        config = BuildingConfig(
            num_floors=num_floors,
            num_elevators=num_elevators,
            capacity=capacity,
            scheduler=SCHEDULER_MAP[scheduler_key](),
            failure_policy=NoFailurePolicy(),
        )
        engine = SimulationEngine(config)
        result = engine.run(requests, failures)

        filename_stem = os.path.splitext(uploaded.filename)[0] or 'upload'
        output_dir = _make_run_dir(filename_stem, scheduler_key)
        write_passenger_summary(result, output_dir)
        write_elevator_positions(result, scheduler_key, output_dir)
        write_summary_txt(result, scheduler_key, output_dir)

        return {
            'status':       'completed',
            'message':      f'Simulation complete. {len(requests)} passengers processed.',
            'output_dir':   output_dir,
            'rows_parsed':  len(requests),
            'rows_skipped': skipped,
            'skip_reasons': skip_reasons,
            'metrics':      format_summary(result),
        }, 200


@ns.route('/upload/compare')
class SimulateUploadCompare(Resource):
    @ns.expect(_upload_compare_parser)
    @ns.response(200, 'Success', upload_compare_response)
    @ns.response(400, 'Validation error')
    def post(self):
        '''Upload a CSV file and run all 3 schedulers side by side.

        The CSV must have a header row with columns: **time, id, source, dest**

        Example file contents:

            time,id,source,dest
            0,p1,1,51
            0,p2,1,37
            10,p3,20,1

        Output files are written to **RunOutput/{filename}/compare/{timestamp}/**.
        Files produced:
        - **passenger_summary.csv** — one row per passenger, columns for each scheduler
        - **cost_elevator_positions.csv**, **nearest_elevator_positions.csv**, **roundrobin_elevator_positions.csv**
        - **summary.txt** — aggregate metrics for all three schedulers
        '''
        args = _upload_compare_parser.parse_args()
        uploaded = args['file']

        if not uploaded.filename.endswith('.csv'):
            api.abort(400, 'Uploaded file must be a .csv')

        num_floors    = args['num_floors']    or 60
        num_elevators = args['num_elevators'] or 3
        capacity      = args['capacity']      or 8

        if not (1 <= num_elevators <= 10):
            api.abort(400, f'num_elevators must be between 1 and 10, got {num_elevators}')

        try:
            requests, skipped, skip_reasons = _parse_csv_stream(uploaded.stream, num_floors)
        except ValueError as e:
            api.abort(400, str(e))

        if not requests:
            api.abort(400, f'No valid passenger rows found. '
                          f'Skipped {skipped} rows: {skip_reasons}')

        failures_file = args.get('failures_file')
        if failures_file and not failures_file.filename.endswith('.csv'):
            api.abort(400, 'Failures file must be a .csv')
        try:
            failures = _parse_failures_stream(failures_file.stream) if failures_file else []
        except ValueError as e:
            api.abort(400, str(e))

        metrics_results = {}
        sim_results = {}
        schedulers = {
            'cost':       CostBasedScheduler(),
            'nearest':    NearestCarScheduler(),
            'roundrobin': RoundRobinScheduler(),
        }
        for name, scheduler in schedulers.items():
            config = BuildingConfig(
                num_floors=num_floors,
                num_elevators=num_elevators,
                capacity=capacity,
                scheduler=scheduler,
                failure_policy=NoFailurePolicy(),
            )
            engine = SimulationEngine(config)
            result = engine.run(requests, failures)
            metrics_results[name] = format_summary(result)
            sim_results[name] = result

        filename_stem = os.path.splitext(uploaded.filename)[0] or 'upload'
        output_dir = _make_run_dir(filename_stem, 'compare')
        write_compare_passenger_summary(sim_results, output_dir)
        write_compare_summary_txt(metrics_results, output_dir)
        for name, result in sim_results.items():
            write_elevator_positions(result, name, output_dir)

        return {
            'status':       'completed',
            'message':      f'Comparison complete. {len(requests)} passengers processed.',
            'output_dir':   output_dir,
            'rows_parsed':  len(requests),
            'rows_skipped': skipped,
            'skip_reasons': skip_reasons,
            'comparison':   metrics_results,
        }, 200


@api.route('/health')
class Health(Resource):
    def get(self):
        '''Health check - confirms the API is running.'''
        return {'status': 'ok', 'service': 'elevator-simulation'}, 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
