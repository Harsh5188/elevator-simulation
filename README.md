# KKR Elevator System Simulation

**Author:** Harsh Verdhan Shukla

A discrete-tick elevator scheduling simulation implementing Cost-Based Dispatch, Round Robin, and Nearest Car algorithms. Built with Strategy + Observer patterns, explicit state machines, and a Flask-RESTX Swagger UI for browser-based interaction.

---

## How to Run

There are two ways to run this project. **Option A (Docker)** is recommended - it requires no Python knowledge. **Option B (Python directly)** works if you prefer not to install Docker.

---

### Option A - Docker (Recommended)

Docker packages everything the project needs into a single container. You do not need Python, pip, or any other tool installed.

#### Step 1 - Check if Docker is already installed

Open a terminal:
- **Windows:** Search "PowerShell" or "cmd" in the Start menu and open it
- **Mac:** Search "Terminal" in Spotlight (Cmd + Space)

Type this and press Enter:
```
docker --version
```

- If you see something like `Docker version 26.x.x` → Docker is installed. Skip to Step 3.
- If you see `'docker' is not recognized` or `command not found` → continue to Step 2.

---

#### Step 2 - Install Docker Desktop

1. Go to **https://www.docker.com/products/docker-desktop**
2. Click **Download for Windows** (or Mac)
3. Run the installer and accept all defaults - do not change any settings
4. **Restart your computer** after installation completes
5. After restarting, search for **Docker Desktop** in your Start menu (Windows) or Applications folder (Mac) and open it
6. Wait until the bottom-left corner of the Docker Desktop window shows a **green icon** and says **"Engine running"** - this can take 1–2 minutes
7. Open a new terminal window and run `docker --version` again to confirm it works

> Docker Desktop must be open and running in the background every time you use these commands. If you restart your computer, open Docker Desktop first before running anything.

---

#### Step 3 - Get the project files

**Option 1 - Download as ZIP (no Git needed):**
1. Go to the GitHub repository page
2. Click the green **Code** button
3. Click **Download ZIP**
4. Unzip the downloaded file to a folder on your Desktop

**Option 2 - If you have Git installed:**
```
git clone https://github.com/Harsh5188/elevator-simulation
```

---

#### Step 4 - Open a terminal inside the project folder

**Windows:**
1. Open the unzipped project folder
2. Hold **Shift** and **right-click** on an empty area inside the folder
3. Select **"Open PowerShell or Terminal window here"**

**Mac:**
1. Right-click the project folder in Finder
2. Select **"New Terminal at Folder"**

---

#### Step 5 - Build and start the application

In the terminal, run:
```
docker compose up --build
```

This will download Python, install all dependencies, and start the application. **The first run takes 2–5 minutes.** Subsequent runs take a few seconds.

Wait until you see a line like:
```
Running on http://localhost:5000 (eg, http://127.0.0.1:5000)
```

>Any time you edit .dockerignore or Dockerfile, run:
```
docker compose build --no-cache
docker compose up
```

---

#### Step 6 - Open the Swagger UI

Open your browser and go to:

**http://localhost:5000/docs**

You will see a visual interface with all available endpoints. To run a simulation:
1. Click **POST /simulate/upload/compare**
2. Click **Try it out**
3. Choose a CSV file using the file picker (format: `time,id,source,dest`)
4. Click **Execute**
5. Results appear in the **Response** panel below. Output files are written to `RunOutput/` inside the container (mount the volume - see CLI section above - to access them on your machine)
6. sample files for request and failure are in **data** folder. 

---

#### Step 7 - Stop the application

Go back to the terminal and press **Ctrl + C**.

---

#### Run the tests (Docker)

Open a **new terminal** in the project folder (keep the app terminal separate) and run:
```
docker compose run --rm elevator-sim python -m pytest tests/ -v
```

---

#### Run via CLI instead of Swagger UI (Docker)

**Windows PowerShell:**
```
docker compose run --rm -v "${PWD}/RunOutput:/app/RunOutput" elevator-sim python main.py --requests data/sample_requests.csv --compare
```

**Mac/Linux:**
```
docker compose run --rm -v "$(pwd)/RunOutput:/app/RunOutput" elevator-sim python main.py --requests data/sample_requests.csv --compare
```

Output CSV files will appear in the `RunOutput/` folder inside your project directory.

---

### Option B - Python directly (no Docker)

Use this if you cannot install Docker or prefer a lighter setup.

#### Step 1 - Check if Python is already installed

Open a terminal (PowerShell on Windows, Terminal on Mac) and run:
```
python --version
```

- If you see `Python 3.10` or higher → skip to Step 3
- If you see `'python' is not recognized` or `command not found` → continue to Step 2

---

#### Step 2 - Install Python

1. Go to **https://www.python.org/downloads**
2. Click the big yellow **Download Python** button
3. Run the installer
4. On the **first screen** of the installer, check the box that says **"Add Python to PATH"** - this box is easy to miss and the project will not work without it
5. Click **Install Now**
6. After installation, **close and reopen your terminal**
7. Run `python --version` again - you should now see a version number

---

#### Step 3 - Navigate to the project folder

In your terminal, type `cd ` (with a space after it), then drag and drop your project folder into the terminal window. The path fills in automatically. Press Enter.

---

#### Step 4 - Install dependencies

```
pip install -r requirements.txt
```

If `pip` is not recognised, try:
```
python -m pip install -r requirements.txt
```

---

#### Step 5 - Run the simulation

Compare all three scheduling algorithms on the sample data:
```
python main.py --requests data/sample_requests.csv --compare
```

Results print in the terminal. Output files appear in the `output/` folder.

---

#### Step 6 - Open the Swagger UI (optional)

If you want the browser interface:
```
python app.py
```
Then open **http://localhost:5000/docs** in your browser. Press **Ctrl+C** to stop.

---

#### Step 7 - Run the tests

```
python -m pytest tests/ -v
```

---

## CLI Options

```
--requests   Path to requests CSV (required)
--failures   Path to failures CSV (optional)
--floors     Number of floors (default: 60)
--elevators  Number of elevators (default: 3)
--capacity   Elevator capacity (default: 8)
--scheduler  cost | nearest | roundrobin (default: cost)
--compare    Run all 3 schedulers and print side-by-side table
```

---

## Input Format

**requests CSV:**
```
time,id,source,dest
0,passenger1,1,51
0,passenger2,1,37
```

**failures CSV (optional):**
```
tick,elevator_id,event
15,E1,fail
25,E1,recover
```

---

## Output Files

All files are written to a timestamped subfolder under `RunOutput/`. See the **Output Files - Full Reference** section at the end of this document for a complete column-by-column guide.

| File | Contents |
|------|----------|
| `RunOutput/{file}/{scheduler}/{ts}/elevator_positions.csv` | Elevator floor and status at every tick |
| `RunOutput/{file}/{scheduler}/{ts}/passenger_summary.csv` | Per-passenger wait, travel, and total times |
| `RunOutput/{file}/{scheduler}/{ts}/summary.txt` | Aggregate metrics across all passengers |
| `RunOutput/{file}/compare/{ts}/passenger_summary.csv` | Merged per-passenger table with one column group per scheduler |
| `RunOutput/{file}/compare/{ts}/{algo}_elevator_positions.csv` | One position file per scheduler in a compare run |
| `RunOutput/{file}/compare/{ts}/summary.txt` | All three schedulers' aggregate metrics in one file |

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `docker` not recognised | Docker Desktop is not installed - follow Step 2 of Option A |
| `docker` not recognised after installing | Restart your computer, then open Docker Desktop and wait for "Engine running" before trying again |
| `docker-compose` not recognised (hyphen) | Use `docker compose` with a space instead - you have Docker V2 |
| Docker Desktop open but commands still fail | Click the Docker Desktop icon in your taskbar/menu bar and confirm it shows "Engine running" in green |
| Port 5000 already in use | Change `5000:5000` to `5001:5000` in `docker-compose.yml`, then visit http://localhost:5001/docs |
| `python` not recognised | Re-run the Python installer and make sure to tick **"Add Python to PATH"** on the first screen |
| `pip` not recognised | Use `python -m pip install -r requirements.txt` instead |
| Tests fail immediately | Make sure you ran `pip install -r requirements.txt` first (Option B only) |
| RunOutput folder is empty | Run the CLI command with the `-v` volume flag (Docker) or check that `RunOutput/` exists in the project directory |
| Swagger UI shows wrong/old endpoints after rebuild | A local `python app.py` process is still running on port 5000 alongside Docker. See the **Port conflict** note below. |

> **Port conflict - local Python vs Docker**
>
> If you have ever run `python app.py` locally and closed the terminal window without pressing `Ctrl+C`, the Python process keeps running silently in the background. When Docker starts, both processes listen on port 5000 and your browser may hit the local one instead of Docker, showing stale endpoints.
>
> **How to detect it:**
> ```
> netstat -ano | findstr :5000
> ```
> If you see more than one process on port 5000, find which one is Python:
> ```
> tasklist /fi "PID eq <pid>"
> ```
> If it says `python.exe`, kill it:
> ```
> taskkill /PID <pid> /F
> ```
> Then refresh the Swagger UI.
>
> **How to avoid it:** always stop the local server with `Ctrl+C` in its terminal before switching to Docker. Alternatively, use the `Makefile` commands below - `make up` automatically clears any process on port 5000 before starting Docker.

---

## Makefile commands (Windows, requires `make`)

The project includes a `Makefile` with shortcuts that handle the port check for you:

| Command | What it does |
|---------|-------------|
| `make up` | Kills any process on port 5000, then starts Docker |
| `make build` | Starts Docker with a rebuild (use after changing code) |
| `make rebuild` | Full clean rebuild ignoring all cache (use after changing `Dockerfile` or `.dockerignore`) |
| `make down` | Stops and removes the container |

> `make` is built into Mac/Linux. On Windows, install it via [Chocolatey](https://chocolatey.org): `choco install make`

---

## Architecture

| Layer | Responsibility |
|-------|----------------|
| `engine/simulation.py` | Tick loop, state transitions, pickup/dropoff |
| `scheduler/` | Strategy pattern - cost-based, nearest car, round robin |
| `observers/` | Observer pattern - metrics collection, position logging |
| `app.py` | Flask-RESTX presentation wrapper only - no simulation logic |
| `main.py` | CLI entry point - no simulation logic |

The engine never imports from the scheduler package. The scheduler receives only the current request and current elevator states - no future visibility into the request queue.

---

## Time Spent

Approximately 8-10 hours. Architecture design and planning 3 hours, core engine + state machines 2 hours, scheduler implementations 2 hour, failure handling 1 hour, tests and output 1-2 hours.

---

## Assumptions and Trade-offs

- One tick = one floor of travel. Door dwell time, acceleration, and deceleration are not modelled - this is a scheduling simulation, not a physics simulation.
- Passengers cannot cancel or modify their request once submitted.
- The scheduler is called once per tick for all unassigned requests. In a real system it would be event-driven.
- Cost function weights (alpha, beta, gamma) are configurable; defaults are chosen to balance wait time against travel time equally.
- Elevator failure recovery is handled via explicit `recover` events in the failures CSV. Recovery time defaults to 10 ticks and is configurable via `--recovery-ticks`.

---

## What I Would Improve With More Time

- **Projected capacity:** track committed future pickups to avoid overcommitting an elevator that will be full before it reaches a new passenger.
- **Zone-based scheduling:** for tall buildings, divide the floor range into bands and dedicate one elevator per band (e.g. floors 1–20, 21–40, 41–60 in a 3-elevator building). A `ZoneBasedScheduler` would extend `SchedulerStrategy` directly - for each incoming request it first filters to only the elevator(s) whose zone covers the passenger's source floor, then runs cost-based selection among those eligible elevators only. The engine, tick loop, and all movement logic stay completely unchanged. The critical addition needed alongside this is a **spillover mechanism**: if a zone's elevator is full or out of service, the scheduler falls back to the nearest available elevator outside the zone rather than leaving the passenger stranded indefinitely. Without spillover, zone-based is strictly worse than cost-based under failure scenarios.
- **Express elevators:** mark certain elevators as express-only (skip floors below N) via an `ExpressRoutingPolicy` injected into the scheduler.
- **Traffic mode patterns:** morning up-peak, evening down-peak. Add a `TrafficModePolicy` that adjusts cost function weights based on time-of-day.
- **WebSocket real-time visualiser:** the Observer pattern makes this straightforward - add a `WebSocketObserver` that pushes elevator positions to a live browser dashboard.

Every improvement above is additive. The simulation engine does not need to change for any of them - they plug in as new policy implementations. This is the explicit design goal of the Strategy + Observer architecture.

---

## Output Files - Full Reference

This section explains every file the simulation writes, what each column means, and how to read the mandatory and notable observations required by the spec.

---

### Where files are written

Every run creates a timestamped subfolder so previous results are never overwritten:

```
RunOutput/
  {input_filename}/
    {scheduler}/          ← single-scheduler run (cost / nearest / roundrobin)
      {YYYYMMDD_HHMMSS}/
        elevator_positions.csv
        passenger_summary.csv
        summary.txt
    compare/              ← compare run (all 3 schedulers at once)
      {YYYYMMDD_HHMMSS}/
        passenger_summary.csv          ← merged, one row per passenger
        cost_elevator_positions.csv
        nearest_elevator_positions.csv
        roundrobin_elevator_positions.csv
        summary.txt
```

**Docker users:** mount the folder with `-v` so files appear on your machine:

```
docker compose run --rm -v "${PWD}/RunOutput:/app/RunOutput" elevator-sim python main.py --requests data/sample_requests.csv --compare
```

---

### elevator_positions.csv

One row per simulation tick starting from tick 0. Records where every elevator was at that moment.

| Column | Meaning |
|--------|---------|
| `tick` | Simulation time step (0, 1, 2, …) |
| `E1`, `E2`, `E3` | Floor number each elevator is on at this tick |
| `E1_status`, `E2_status`, `E3_status` | State of each elevator: `idle`, `moving_up`, `moving_down`, or `out_of_service` |

**How to read it:** open the file and find the row where `tick` matches the moment you care about. Each `E#` column tells you that elevator's exact floor. Useful for verifying an elevator reached a pickup floor at the right time, or for spotting if an elevator sat idle while passengers were waiting.

In a compare run, each scheduler gets its own file (`cost_elevator_positions.csv`, etc.) so you can open them side by side and see how routing decisions differed tick by tick.

---

### passenger_summary.csv (single run)

One row per passenger. Covers the full lifecycle of each journey.

| Column | Meaning |
|--------|---------|
| `passenger_id` | ID from the input CSV |
| `source` | Floor the passenger started on |
| `destination` | Floor the passenger requested to reach |
| `request_tick` | Tick when the passenger submitted their request |
| `assigned_elevator` | Which elevator was dispatched to them |
| `pickup_tick` | Tick when they boarded the elevator |
| `dropoff_tick` | Tick when they arrived at their destination |
| `wait_time` | Ticks between request and boarding (`pickup_tick - request_tick`) |
| `travel_time` | Ticks spent riding (`dropoff_tick - pickup_tick`) |
| `total_time` | End-to-end ticks (`dropoff_tick - request_tick`) |
| `reassign_count` | Times this passenger was re-queued (0 = no failure affected them) |

---

### passenger_summary.csv (compare run)

Same rows as above but the per-scheduler columns repeat for each algorithm. Columns follow this pattern:

```
passenger_id, source, destination, request_tick,
cost_assigned_elevator, cost_pickup_tick, cost_dropoff_tick, cost_wait_time, cost_travel_time, cost_total_time, cost_reassign_count,
nearest_assigned_elevator, nearest_pickup_tick, ...
roundrobin_assigned_elevator, roundrobin_pickup_tick, ...
```

**How to read it:** each row is one passenger. Scan across the `*_wait_time` columns to see at a glance which scheduler picked them up fastest. Passengers that experienced very different wait times across schedulers are the ones that reveal the most about each algorithm's strengths.

---

### summary.txt

Aggregate statistics across all delivered passengers for a single run (or all three schedulers in a compare run).

---

### Mandatory observations (required by spec)

These are the metrics the spec explicitly requires the simulation to report. You will find all of them in `summary.txt` and in the JSON response from the API.

| Metric | Where to find it | What it tells you |
|--------|-----------------|-------------------|
| `min_wait_time` | `summary.txt`, API response | Best-case time from request to pickup - shows how fast the system can respond when conditions are ideal |
| `avg_wait_time` | `summary.txt`, API response | Typical experience for a passenger |
| `max_wait_time` | `summary.txt`, API response | Worst-case wait - flags any passenger who was left waiting much longer than average |
| `min_total_time` | `summary.txt`, API response | Fastest end-to-end journey (short trip + immediate pickup) |
| `avg_total_time` | `summary.txt`, API response | Typical end-to-end journey time |
| `max_total_time` | `summary.txt`, API response | Worst end-to-end journey - combines the worst wait with the longest ride |

---

### Notable observations (additional insights)

These go beyond the mandatory minimums and reveal the shape of the distribution and system behaviour.

| Metric | Where to find it | What it tells you |
|--------|-----------------|-------------------|
| `p95_wait_time` | `summary.txt`, API response | 95th-percentile wait time - the worst wait experienced by the bottom 95% of passengers, excluding extreme outliers. A large gap between `avg_wait_time` and `p95_wait_time` means a small number of passengers waited significantly longer than everyone else. |
| `p95_total_time` | `summary.txt`, API response | Same idea for end-to-end time. Useful for spotting whether the tail experience (the slowest 5%) is proportionally worse than the average. |
| `reassigned_count` | `summary.txt`, API response | Number of passengers who were re-queued because an elevator failed mid-service. Zero on normal runs; non-zero only when a failures CSV is provided. A high number indicates failures happened at moments that disrupted many passengers at once. |
| Per-passenger columns in compare CSV | `passenger_summary.csv` | By comparing `cost_wait_time` vs `nearest_wait_time` vs `roundrobin_wait_time` for the same passenger, you can see which scheduler served each individual best. Passengers with high variance across schedulers are the cases where algorithm choice matters most. |
| Elevator utilisation (by inspection) | `elevator_positions.csv` | Count the ticks where `E#_status` is `idle` versus `moving_up` / `moving_down`. A high idle fraction means that elevator was underused - useful for deciding whether fewer elevators would suffice. |

---

### Design decisions

- **Elevator count validated to 1–10.** The spec states this is a hard requirement. Floors and capacity have no upper bound.
- **CSV-upload-only API.** The JSON body endpoints (`POST /simulate/` and `POST /simulate/compare`) were removed. The Swagger UI exposes only CSV upload endpoints, which are more practical for the volume of data a real test involves.
- **Output folder renamed to `RunOutput/`.** Subfolders are structured as `RunOutput/{input_filename}/{scheduler}/{YYYYMMDD_HHMMSS}/` so multiple runs on the same file and same algorithm never overwrite each other.
- **Compare mode produces a merged `passenger_summary.csv`.** Rather than three separate files that must be opened and manually cross-referenced, a single file contains all passengers as rows with per-scheduler columns side by side.
- **Compare mode produces per-scheduler elevator position files.** One file per algorithm (`cost_elevator_positions.csv`, etc.) so tick-by-tick routing can be compared without merging files manually.
- **`projected_stops` excludes assigned destinations.** An elevator only commits to stopping at a floor to pick someone up, not at their destination, until they are actually onboard. Including assigned destinations caused IDLE elevators to target a floor they had no reason to visit yet, producing a deadlock with round-robin scheduling.
