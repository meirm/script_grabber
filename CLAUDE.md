# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ScriptGrabber is a distributed job scheduling system using a master-grabber architecture. It implements a file-based polling mechanism where:
- Jobs are submitted as Python scripts to a shared queue directory
- Multiple grabber instances monitor the queue and execute jobs
- All coordination happens via shared filesystem (no database required)
- Signal-based control for pause/resume/status operations

## Core Architecture

### Master-Grabber Pattern
The system uses a distributed architecture with two main components:

**Grabber** (`src/script_grabber/grabber.py`):
- Worker instances that poll queues for jobs
- Each grabber has a unique name and dedicated spool directory
- Jobs are executed as subprocess calls to Python scripts
- Implements file-based locking to prevent duplicate execution
- Supports two queue priorities: control queue (higher) and common queue

**GrabMaster** (`src/script_grabber/grabmaster.py`):
- Currently a stub for future job scheduling logic
- Intended to manage job distribution and monitoring

### Directory Structure
The cluster operates with this filesystem layout:
```
<clusterpath>/
├── queue/           # Common job queue (all grabbers monitor)
├── ctrl/<name>/     # Per-grabber control queue (higher priority)
├── spool/<name>/    # Per-grabber job execution directory
├── log/             # Execution logs and grabber logs
└── varlock/         # Lock files for grabber instances
```

### Job Lifecycle
1. **Queued**: Job script placed in `queue/` or `ctrl/<name>/`
2. **Grabbed**: Moved to `spool/<name>/<job>-<timestamp>`
3. **Running**: Renamed with `-RUNNING` suffix, made executable (0o755)
4. **Completed**: Renamed to `-DONE`, `-FAILED`, or `-TIMEOUT` based on exit code
5. **Logged**: stdout/stderr written to `.out`/`.err` files, summary in `.log`

Exit codes: 0 = success (DONE), 124 = timeout (TIMEOUT), other = failure (FAILED)

### Signal Handling
- **SIGINT**: Graceful shutdown - stops execution, removes lock file, exits
- **SIGUSR1**: Status dump (currently prints to stdout, implementation incomplete)
- **SIGUSR2**: Pause/resume toggle for polling loop

### Exception Hierarchy
Defined in `src/script_grabber/grabexceptions.py`:
- `GrabError`: Base exception
  - `GrabTimeoutError`
  - `GrabConnectionError`
  - `GrabNetworkError`
  - `GrabMisuseError`
  - `GrabConfigError`
  - `GrabLockError`

Note: `GrabLockError` is raised but not properly propagated in `grabber.py:150` (bug)

## Development Commands

### Setup and Installation
```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Build the project
uv build

# Install in development mode
uv pip install -e .

# Install with development dependencies (pytest)
uv pip install -e ".[dev]"
```

### Running Grabbers
```bash
# Direct execution
python -m script_grabber.grabber <name> <cluster_path> [--job-timeout SECONDS]

# Using CLI entry point (after install)
grabber <name> <cluster_path> [--job-timeout SECONDS]

# Example
grabber worker1 /shared/cluster --job-timeout 3600
```

### Docker Deployment
```bash
# Build and run with docker-compose
# Set environment variables: GRABMASTER_NAME, GRABBER_NAME, CLUSTER_PATH
docker-compose up -d

# Single container
docker build -t script_grabber .
docker run -v /path/to/cluster:/cluster script_grabber worker1 /cluster
```

### Testing Jobs
Create a test job script and place it in the queue:
```bash
# Create test job
echo '#!/usr/bin/env python3
print("Hello from job")
' > /shared/cluster/queue/test_job.py

# Watch the spool directory for execution
watch -n 1 'ls -ltr /shared/cluster/spool/worker1/'
```

### Controlling Running Grabbers
```bash
# Find grabber PID
ps aux | grep grabber

# Pause/resume polling
kill -SIGUSR2 <PID>

# Request status dump
kill -SIGUSR1 <PID>

# Graceful shutdown
kill -SIGINT <PID>
```

## Key Implementation Notes

### Lock File Management
- Lock files prevent duplicate grabber instances with the same name
- Located at `<varlock>/<name>.lock` containing the PID
- **Bug**: Line 150 raises `GrabLockError` but doesn't actually stop execution
- Locks are only removed on SIGINT, not on other exits (potential stale locks)

### Job Execution
- Jobs run as subprocesses using `subprocess.run()` with cwd set to clusterpath
- stdout/stderr are captured and written to separate `.out`/`.err` files
- No timeout enforcement is implemented despite `job_timeout` parameter
- Jobs must be valid Python scripts (executed via `sys.executable`)

### Race Condition Handling
- `FileNotFoundError` during job grab is caught and ignored (another grabber got it)
- Jobs are moved atomically to spool before execution begins
- No explicit file locking beyond the grabber instance lock

### Configuration Defaults
From `grabber.py:133-141`:
- Control queue: `<clusterpath>/ctrl/<name>`
- Common queue: `<clusterpath>/queue`
- Spool: `<clusterpath>/spool/<name>`
- Log directory: `<clusterpath>/log`
- Varlock: `<clusterpath>/varlock`
- Job timeout: 3600 seconds (not enforced)
- Sleep time: 10 seconds between poll cycles

### Known Issues
1. `GrabLockError` raised but doesn't prevent execution (line 150)
2. Job timeout parameter exists but timeout is never enforced
3. SIGUSR1 status dump is incomplete
4. No cleanup of stale lock files on abnormal termination
5. Duplicate import of `time` module (lines 21, 30)
6. `GrabError` exception defined twice (in both `grabber.py` and `grabexceptions.py`)
