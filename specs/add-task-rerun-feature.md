# Feature: Task Rerun Capability

## Feature Description
Add the ability to rerun completed, failed, or timed-out tasks by copying the task script with a new timestamp to a temporary directory and then moving it into the queue to be picked up by any available grabber. This feature enables users to retry failed jobs, re-execute successful jobs with the same logic, or investigate issues by running tasks again without manually recreating the job script.

The rerun feature will:
- Support rerunning tasks from any final state (DONE, FAILED, TIMEOUT)
- Generate a new timestamped copy to maintain job history
- Work with both command-line interface and programmatic usage
- Preserve the original job script while creating a new execution instance
- Support rerunning jobs into either the common queue or a specific grabber's control queue

## User Story
As a **system administrator or developer**
I want to **rerun a previously executed task (whether it succeeded, failed, or timed out)**
So that **I can retry failed operations, re-execute successful workflows, or investigate issues without manually recreating job scripts**

## Problem Statement
Currently, once a job is executed by a grabber, it moves through states (RUNNING → DONE/FAILED/TIMEOUT) and remains in the spool directory. If a user needs to:
- Retry a failed job due to transient errors
- Re-execute a successful job with the same logic
- Debug a timeout issue by running the job again
- Repeat a workflow without manual script creation

They must manually:
1. Locate the completed job in the spool directory
2. Copy the script file
3. Remove the status suffix (-DONE, -FAILED, -TIMEOUT)
4. Remove the timestamp
5. Place it in the appropriate queue

This manual process is error-prone, time-consuming, and doesn't scale for automated workflows or frequent reruns.

## Solution Statement
Implement a `rerun_task()` method in the Grabber class and a CLI command `grabber-rerun` that:

1. **Locates** the specified completed task in the spool directory by job name
2. **Validates** the task exists and is in a final state (DONE/FAILED/TIMEOUT)
3. **Creates** a temporary copy of the job script in a dedicated temp directory
4. **Moves** the copy to the specified queue (common or control) with the original job name
5. **Logs** the rerun operation for audit trail

The solution will be implemented as:
- A core method `rerun_task()` in the Grabber class for programmatic usage
- A CLI entry point `grabber-rerun` for command-line usage
- Proper error handling for missing files, invalid states, and permission issues
- Comprehensive logging of rerun operations

## Relevant Files
Use these files to implement the feature:

### Existing Files to Modify

- **`src/script_grabber/grabber.py`** (lines 52-253)
  - Core Grabber class where the `rerun_task()` method will be implemented
  - Contains job lifecycle logic (grab_job, run_job) that provides context for rerun behavior
  - Already has logging infrastructure and directory management utilities
  - Need to add rerun_task method that locates completed jobs and copies them to queue

- **`src/script_grabber/grabexceptions.py`**
  - Define new exception types for rerun-specific errors
  - Add `GrabRerunError` for general rerun failures
  - Add `GrabTaskNotFoundError` for missing task files
  - Maintain consistency with existing exception hierarchy

- **`pyproject.toml`** (lines 25-26)
  - Add new CLI entry point for `grabber-rerun` command
  - Register the new command in `[project.scripts]` section
  - Follows existing pattern: `grabber = "script_grabber.grabber:main"`

### New Files

- **`src/script_grabber/rerun.py`**
  - New module for rerun-specific logic
  - Contains `main()` function for CLI entry point
  - Handles argument parsing for rerun command
  - Provides user-friendly interface for rerunning tasks
  - Arguments: grabber_name, cluster_path, job_name, --queue-type (common|control)

- **`tests/unit/test_rerun.py`**
  - Unit tests for rerun functionality
  - Tests rerun_task method with various scenarios
  - Mocks file system operations for fast, isolated tests
  - Tests error conditions and edge cases

- **`tests/integration/test_rerun_integration.py`**
  - Integration tests with real file system operations
  - Tests complete rerun workflow: DONE → rerun → RUNNING → DONE
  - Tests rerun of FAILED and TIMEOUT jobs
  - Tests rerun to control queue vs common queue
  - Verifies job history preservation and logging

## Implementation Plan

### Phase 1: Foundation
Establish the core rerun infrastructure by:
1. Defining new exception types specific to rerun operations in `grabexceptions.py`
2. Creating the rerun module structure in `src/script_grabber/rerun.py`
3. Setting up the CLI entry point infrastructure in `pyproject.toml`

This foundation ensures proper error handling, separation of concerns, and CLI accessibility before implementing core logic.

### Phase 2: Core Implementation
Implement the rerun logic by:
1. Adding the `rerun_task()` method to the Grabber class with complete job lifecycle handling
2. Implementing task discovery logic to locate completed jobs in spool directories
3. Adding temporary directory management for safe file operations
4. Implementing atomic move operations to prevent race conditions
5. Adding comprehensive logging for audit trails

### Phase 3: Integration
Connect the rerun feature to the existing system by:
1. Implementing the CLI interface in `rerun.py` with argument parsing and validation
2. Creating comprehensive tests (unit and integration) to verify functionality
3. Validating the complete workflow from CLI usage to job re-execution
4. Ensuring proper error handling and user feedback throughout the process

## Step by Step Tasks

### 1. Define Rerun-Specific Exceptions
- Open `src/script_grabber/grabexceptions.py`
- Add `GrabRerunError` class inheriting from `GrabError` for general rerun failures
- Add `GrabTaskNotFoundError` class inheriting from `GrabRerunError` for missing task scenarios
- Add docstrings explaining when each exception should be raised

### 2. Implement Core rerun_task Method in Grabber Class
- Open `src/script_grabber/grabber.py`
- Import new exception types from `grabexceptions.py`
- Add `rerun_task(self, job_name: str, target_queue: str = "common") -> str` method
- Implement logic to:
  - Search spool directory for job files matching pattern `{job_name}*-(DONE|FAILED|TIMEOUT)`
  - Raise `GrabTaskNotFoundError` if no matching job found
  - Extract the original job name by removing timestamp and status suffixes
  - Create temporary directory if it doesn't exist: `{clusterpath}/temp`
  - Copy job file to temp directory with original name
  - Determine target queue path based on `target_queue` parameter
  - Use atomic move operation to place job in target queue
  - Log rerun operation with original location and new queue location
  - Return path to the requeued job file
- Add comprehensive error handling for file operations
- Add logging statements for each major step

### 3. Create Rerun CLI Module
- Create `src/script_grabber/rerun.py`
- Import necessary modules: `argparse`, `logging`, `sys`, `Path`
- Import `Grabber` class and rerun exceptions
- Implement `main()` function with:
  - Argument parser setup with positional args: `grabber_name`, `cluster_path`, `job_name`
  - Optional argument: `--queue-type` with choices=['common', 'control'] (default='common')
  - Logging configuration using existing Grabber logging pattern
  - Grabber instance creation (without calling `run()`)
  - Call to `rerun_task()` method with appropriate parameters
  - User-friendly success/error messages
  - Proper exit codes: 0 for success, 1 for errors
- Add error handling with try/except for `GrabTaskNotFoundError` and general exceptions
- Add `if __name__ == "__main__": main()` block

### 4. Register CLI Entry Point
- Open `pyproject.toml`
- In `[project.scripts]` section, add new entry point:
  ```toml
  grabber-rerun = "script_grabber.rerun:main"
  ```
- Ensure it follows the same pattern as existing `grabber` entry point

### 5. Create Unit Tests for Rerun Functionality
- Create `tests/unit/test_rerun.py`
- Import necessary testing modules and fixtures
- Add test class `TestRerunTask` with tests for:
  - `test_rerun_done_job_to_common_queue`: Successfully rerun a DONE job
  - `test_rerun_failed_job_to_common_queue`: Successfully rerun a FAILED job
  - `test_rerun_timeout_job_to_control_queue`: Successfully rerun TIMEOUT job to control queue
  - `test_rerun_nonexistent_job_raises_exception`: Verify `GrabTaskNotFoundError` raised
  - `test_rerun_creates_temp_directory`: Verify temp dir creation
  - `test_rerun_preserves_original_job`: Verify original job file unchanged
  - `test_rerun_generates_correct_job_name`: Verify job name formatting
- Use mocking for file operations to keep tests fast and isolated
- Add pytest markers: `@pytest.mark.unit`

### 6. Create Integration Tests for Rerun Workflow
- Create `tests/integration/test_rerun_integration.py`
- Import necessary modules and use existing fixtures from `conftest.py`
- Create new fixtures:
  - `completed_done_job`: Fixture that creates and runs a job to DONE state
  - `completed_failed_job`: Fixture that creates and runs a job to FAILED state
  - `completed_timeout_job`: Fixture that creates and runs a job to TIMEOUT state
- Add test class `TestRerunIntegration` with tests for:
  - `test_rerun_done_job_end_to_end`: Full workflow - create job → run → complete → rerun → verify new execution
  - `test_rerun_failed_job_with_fix`: Rerun a failed job that can succeed on retry
  - `test_rerun_preserves_job_history`: Verify original job remains in spool after rerun
  - `test_rerun_to_control_queue`: Verify job appears in correct control queue
  - `test_rerun_multiple_times`: Verify same job can be rerun multiple times
  - `test_concurrent_rerun_attempts`: Test race condition handling when multiple rerun attempts occur
- Use real file system operations via `temp_cluster_path` fixture
- Add pytest markers: `@pytest.mark.integration`
- Verify logging output contains expected rerun operation messages

### 7. Add CLI Tests for grabber-rerun Command
- Add tests to `tests/integration/test_rerun_integration.py`
- Add test class `TestRerunCLI` with tests for:
  - `test_cli_rerun_success`: Test successful CLI execution
  - `test_cli_rerun_nonexistent_job`: Test CLI error handling
  - `test_cli_rerun_with_queue_type_flag`: Test --queue-type parameter
  - `test_cli_rerun_exit_codes`: Verify correct exit codes
- Use `subprocess.run()` to invoke CLI command
- Parse stdout/stderr for expected messages
- Add pytest markers: `@pytest.mark.integration`

### 8. Update Grabber ensure_dirs Method
- Open `src/script_grabber/grabber.py`
- Locate `ensure_dirs()` method (line 168)
- Add creation of temp directory: `os.makedirs(os.path.join(self.clusterpath, "temp"), exist_ok=True)`
- This ensures the temp directory exists for rerun operations

### 9. Add Logging Configuration for Rerun Operations
- Open `src/script_grabber/rerun.py`
- In `main()` function, configure logging similar to Grabber class
- Use log file: `{cluster_path}/log/rerun.log`
- Set log level to INFO
- Use format: `[%(asctime)s][%(levelname)s] %(message)s`

### 10. Run All Tests and Validate Zero Regressions
- Execute all test commands from the Validation Commands section
- Verify all existing tests pass without modification
- Verify all new rerun tests pass
- Check test coverage remains ≥80%
- Fix any failing tests or regressions

## Testing Strategy

### Unit Tests
**File**: `tests/unit/test_rerun.py`

**Coverage**:
- `rerun_task()` method with mocked file operations
- Exception handling for missing jobs
- Temp directory creation logic
- Job name extraction and formatting
- Queue path determination logic

**Key Tests**:
- Successful rerun with all job states (DONE, FAILED, TIMEOUT)
- Error handling for nonexistent jobs
- Correct file paths and names generated
- Logging messages generated correctly

### Integration Tests
**File**: `tests/integration/test_rerun_integration.py`

**Coverage**:
- End-to-end rerun workflow with real file system
- Job history preservation
- Multiple rerun attempts on same job
- Rerun to different queue types
- CLI command execution and output
- Concurrent rerun attempt handling

**Key Tests**:
- Complete lifecycle: job execution → completion → rerun → re-execution
- Job file preservation in spool directory
- Correct queue placement (common vs control)
- Atomic operations prevent race conditions
- CLI interface usability and error messages

### Edge Cases
1. **Nonexistent job name**: Verify `GrabTaskNotFoundError` raised with helpful message
2. **Multiple jobs with same base name**: Ensure most recent job is selected
3. **Job in RUNNING state**: Verify rerun is not allowed (or handle appropriately)
4. **Concurrent rerun attempts**: Verify atomic operations prevent corruption
5. **Missing permissions**: Handle permission denied errors gracefully
6. **Disk space exhaustion**: Handle copy failures with appropriate error messages
7. **Invalid queue type**: Validate queue type parameter and provide helpful errors
8. **Empty job file**: Handle corrupted or empty job files
9. **Temp directory cleanup**: Verify temp files don't accumulate

## Acceptance Criteria
1. ✅ `rerun_task()` method successfully copies completed jobs to queue
2. ✅ CLI command `grabber-rerun` is accessible and functional
3. ✅ Rerun works for all final job states: DONE, FAILED, TIMEOUT
4. ✅ Original job files remain unchanged in spool directory
5. ✅ New job appears in specified queue (common or control) with correct name
6. ✅ Rerun operations are logged with source and destination paths
7. ✅ Missing jobs raise `GrabTaskNotFoundError` with helpful message
8. ✅ Temp directory is created automatically if missing
9. ✅ Multiple reruns of the same job are supported
10. ✅ CLI provides clear success/error messages to users
11. ✅ All unit tests pass (≥80% coverage maintained)
12. ✅ All integration tests pass with real file operations
13. ✅ No regressions in existing grabber functionality
14. ✅ Documentation in code includes docstrings and comments

## Validation Commands
Execute every command to validate the feature works correctly with zero regressions.

```bash
# Install package in development mode with test dependencies
uv pip install -e ".[dev]"

# Run all existing tests to ensure no regressions
uv run pytest -v

# Run only unit tests (should be fast)
uv run pytest -m unit -v

# Run only integration tests
uv run pytest -m integration -v

# Run new rerun-specific tests
uv run pytest tests/unit/test_rerun.py -v
uv run pytest tests/integration/test_rerun_integration.py -v

# Check test coverage (should maintain ≥80%)
uv run pytest --cov=src/script_grabber --cov-report=term-missing

# Verify CLI command is registered and accessible
grabber-rerun --help

# Manual end-to-end test: Create a test cluster and rerun a job
# 1. Create test cluster structure
mkdir -p /tmp/test_cluster/{queue,ctrl,spool,log,varlock,temp}

# 2. Create a simple test job
echo '#!/usr/bin/env python3
print("Test job executed")
exit(0)' > /tmp/test_cluster/queue/test_job.py

# 3. Run grabber to execute the job (in background, will auto-stop after job)
timeout 30s grabber test_grabber /tmp/test_cluster --job-timeout 10 || true

# 4. Verify job completed (should see DONE file in spool)
ls -la /tmp/test_cluster/spool/test_grabber/

# 5. Rerun the completed job
grabber-rerun test_grabber /tmp/test_cluster test_job.py

# 6. Verify job reappeared in queue
ls -la /tmp/test_cluster/queue/

# 7. Run grabber again to execute the rerun job
timeout 30s grabber test_grabber /tmp/test_cluster --job-timeout 10 || true

# 8. Verify second execution completed
ls -la /tmp/test_cluster/spool/test_grabber/ | grep DONE

# 9. Cleanup test cluster
rm -rf /tmp/test_cluster

# Run full test suite one final time
uv run pytest
```

## Notes

### Implementation Details
- The `rerun_task()` method uses a search pattern to locate completed jobs in the spool directory, allowing flexibility in matching jobs with timestamps and status suffixes
- Temporary directory (`{clusterpath}/temp`) is used as an intermediate step to ensure atomic operations and prevent race conditions
- The original job file in the spool directory is never modified, preserving the audit trail of past executions
- Job name extraction handles the format: `{original_name}-{timestamp}-{STATUS}` → `{original_name}.py`

### Future Enhancements
Consider implementing in future iterations:
1. **Bulk rerun**: Rerun multiple jobs at once using pattern matching
2. **Rerun with modifications**: Allow parameter changes before rerun
3. **Scheduled reruns**: Automatically retry failed jobs after a delay
4. **Rerun history tracking**: Maintain metadata about which jobs are reruns
5. **Web interface integration**: Add rerun button to web UI for visual management
6. **Conditional rerun**: Only rerun if certain conditions are met (e.g., only if failed)

### Security Considerations
- Validate job file paths to prevent directory traversal attacks
- Ensure proper file permissions are maintained during copy operations
- Log all rerun operations for audit compliance
- Consider adding authentication/authorization for production deployments

### Performance Considerations
- Rerun operation is fast (single file copy + move)
- No impact on running grabbers or active jobs
- Temp directory should be on same filesystem as queue for atomic moves
- Consider periodic cleanup of temp directory if reruns are interrupted
