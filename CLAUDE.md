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

## Testing

### Test Suite Overview

ScriptGrabber has a comprehensive test suite with 80%+ coverage:
- **Unit tests**: Fast, isolated tests for individual components
- **Integration tests**: Real file system operations and job lifecycle
- **End-to-end tests**: Full distributed scenarios with multiple grabbers

### Running Tests

```bash
# Install test dependencies
uv pip install -e ".[dev]"

# Run all tests
uv run pytest -v

# Run specific test categories
uv run pytest -m unit -v           # Unit tests only
uv run pytest -m integration -v    # Integration tests only
uv run pytest -m e2e -v            # End-to-end tests only

# Generate coverage report
uv run pytest --cov=src/script_grabber --cov-report=term-missing
uv run pytest --cov=src/script_grabber --cov-report=html

# Run specific test file
uv run pytest tests/unit/test_grabber.py -v

# Run tests matching pattern
uv run pytest -k "signal" -v      # All signal-related tests
uv run pytest -k "multi_grabber" -v  # Multi-grabber tests
```

### Test File Organization

```
tests/
├── conftest.py              # Shared fixtures and configuration
├── fixtures/
│   ├── __init__.py
│   └── sample_jobs.py       # Sample job scripts for testing
├── unit/
│   ├── test_exceptions.py   # Exception hierarchy tests
│   └── test_grabber.py      # Grabber class unit tests
├── integration/
│   ├── test_job_lifecycle.py    # Complete job lifecycle tests
│   ├── test_signal_handling.py  # Signal handling tests
│   ├── test_multi_grabber.py    # Multi-grabber scenarios
│   └── test_edge_cases.py       # Edge cases and error conditions
└── e2e/
    └── test_distributed_scenario.py  # Full distributed tests
```

### Test Fixtures

The test suite provides reusable fixtures in `tests/conftest.py`:
- `temp_cluster_path`: Temporary cluster directory structure
- `sample_grabber`: Pre-configured Grabber instance
- `mock_job_success`: Job that exits with code 0
- `mock_job_failure`: Job that exits with code 1
- `mock_job_timeout`: Job that simulates timeout (exit 124)
- `multiple_jobs`: Multiple jobs in common queue
- `ctrl_queue_job`: Job in control queue

### Writing New Tests

When adding new tests:
1. Use appropriate pytest markers (`@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.e2e`)
2. Use existing fixtures from `conftest.py` when possible
3. Follow naming convention: `test_<component>_<behavior>.py`
4. Add docstrings explaining what is being tested
5. Keep unit tests fast and isolated
6. Use integration tests for file system operations
7. Use e2e tests for full system scenarios

### Debugging Failed Tests

```bash
# Run with verbose output
uv run pytest -vv

# Show print statements
uv run pytest -s

# Run specific test
uv run pytest tests/unit/test_grabber.py::TestGrabberInitialization::test_init_with_required_params_only -v

# Drop into debugger on failure
uv run pytest --pdb

# Show local variables on failure
uv run pytest -l
```

### Known Issues Documented in Tests

The test suite documents several known issues:
1. **Line 150 bug**: `GrabLockError` raised but doesn't prevent execution (missing `raise` keyword)
2. **Timeout not enforced**: `job_timeout` parameter exists but timeout never enforced
3. **SIGUSR1 incomplete**: Status dump implementation incomplete

These are tested to document current behavior and will need updates when bugs are fixed.
- do not use alerts or modals in the frontend.