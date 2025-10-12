# Chore: Add Unit Tests and End-to-End Tests

## Chore Description
Implement comprehensive unit tests and end-to-end (E2E) tests for the ScriptGrabber distributed job scheduling system. The project currently has pytest configured as a development dependency but lacks any test files or test coverage. This chore will establish a robust test suite covering:
- Unit tests for individual components (Grabber class, exceptions, utilities)
- Integration tests for file system operations and job lifecycle
- End-to-end tests simulating real-world multi-grabber scenarios
- Signal handling and concurrency tests
- Edge cases and error conditions

The test suite will ensure code reliability, prevent regressions, and serve as living documentation for the system's behavior.

## Relevant Files
Use these files to resolve the chore:

- `src/script_grabber/grabber.py` - Main Grabber class that needs comprehensive unit and integration testing. Contains job grabbing logic, job execution, signal handling, and file system operations.
- `src/script_grabber/grabexceptions.py` - Custom exception hierarchy that needs testing for proper instantiation and inheritance.
- `src/script_grabber/grabmaster.py` - Currently a stub but should have basic tests for future expansion.
- `src/script_grabber/__init__.py` - Package initialization file that may need testing for proper exports.
- `pyproject.toml` - Contains pytest configuration. May need to add test dependencies (pytest-timeout, pytest-cov, pytest-mock).
- `README.md` - Needs to be updated with test execution instructions.
- `CLAUDE.md` - Developer guidance document that should include testing workflows and best practices.

### New Files
- `tests/__init__.py` - Test package initialization
- `tests/conftest.py` - Pytest configuration and shared fixtures (temporary directories, mock cluster setup, sample job scripts)
- `tests/unit/test_grabber.py` - Unit tests for Grabber class methods
- `tests/unit/test_exceptions.py` - Unit tests for exception hierarchy
- `tests/unit/test_grabmaster.py` - Unit tests for GrabMaster class (when implemented)
- `tests/integration/test_job_lifecycle.py` - Integration tests for complete job lifecycle (queued → running → done/failed)
- `tests/integration/test_signal_handling.py` - Tests for SIGINT, SIGUSR1, SIGUSR2 signal handling
- `tests/integration/test_multi_grabber.py` - Tests for multiple grabbers competing for jobs
- `tests/e2e/test_distributed_scenario.py` - End-to-end tests simulating real distributed cluster scenarios
- `tests/fixtures/sample_jobs.py` - Sample job scripts for testing (success, failure, timeout scenarios)

## Step by Step Tasks
IMPORTANT: Execute every step in order, top to bottom.

### 1. Set up test infrastructure and dependencies
- Create `tests/` directory structure with subdirectories: `unit/`, `integration/`, `e2e/`, `fixtures/`
- Create `tests/__init__.py` files in all test directories
- Update `pyproject.toml` to add additional test dependencies:
  - `pytest-timeout` for timeout testing
  - `pytest-cov` for coverage reporting
  - `pytest-mock` for mocking support
  - `pytest-asyncio` if async support is needed
- Configure pytest settings in `pyproject.toml` under `[tool.pytest.ini_options]`:
  - Test discovery patterns
  - Coverage settings
  - Timeout defaults
  - Markers for different test types (unit, integration, e2e)

### 2. Create shared test fixtures and utilities
- Create `tests/conftest.py` with reusable fixtures:
  - `temp_cluster_path` - Temporary directory structure mimicking cluster filesystem
  - `sample_grabber` - Pre-configured Grabber instance for testing
  - `mock_job_success` - Sample job script that exits with code 0
  - `mock_job_failure` - Sample job script that exits with code 1
  - `mock_job_timeout` - Sample job script that simulates timeout (exit code 124)
  - `cleanup_locks` - Fixture to clean up lock files after tests
- Create `tests/fixtures/sample_jobs.py` with various test job scripts:
  - Simple success job (prints output and exits 0)
  - Failure job (raises exception, exits non-zero)
  - Long-running job (sleeps for configurable time)
  - Job that writes to stdout/stderr
  - Job that uses environment variables

### 3. Write unit tests for exception hierarchy
- Create `tests/unit/test_exceptions.py`
- Test that all exception classes can be instantiated with proper messages
- Test inheritance chain: GrabError → specific exceptions
- Test that exceptions can be caught by base class
- Verify exception messages are preserved correctly

### 4. Write unit tests for Grabber initialization and configuration
- Create `tests/unit/test_grabber.py` for Grabber class tests
- Test `__init__()` with various parameter combinations
- Test `defaults()` method applies correct default paths
- Test `ensure_dirs()` creates all required directories
- Test logging configuration is set up correctly
- Test signal handlers are registered (SIGINT, SIGUSR1, SIGUSR2)
- Verify that duplicate instance detection raises GrabLockError (test bug at line 150)

### 5. Write unit tests for job grabbing logic
- Add tests to `tests/unit/test_grabber.py` for `grab_job()` method
- Test grabbing from control queue (higher priority)
- Test grabbing from common queue when control queue is empty
- Test that jobs are moved to spool directory with timestamp
- Test that jobs are renamed with -RUNNING suffix
- Test that file permissions are set to executable (0o755)
- Test FileNotFoundError handling when another grabber takes the job
- Test that None is returned when no jobs are available

### 6. Write unit tests for job execution logic
- Add tests to `tests/unit/test_grabber.py` for `run_job()` method
- Test successful job execution (exit code 0 → -DONE suffix)
- Test failed job execution (non-zero exit code → -FAILED suffix)
- Test timeout job execution (exit code 124 → -TIMEOUT suffix)
- Test stdout/stderr capture and writing to .out/.err files
- Test log file creation with job name, timestamp, exit code
- Test that job file is moved to appropriate destination based on exit code
- Test handling of non-existent job files

### 7. Write unit tests for signal handling
- Add tests to `tests/unit/test_grabber.py` for signal handler methods
- Test `handle_sigint()` sets is_running=False and removes lock file
- Test `handle_usr1()` dumps status (when implemented)
- Test `handle_usr2()` toggles is_paused flag correctly
- Mock signal delivery and verify handler behavior
- Test that SIGINT cleanup removes lock file from varlock directory

### 8. Write integration tests for complete job lifecycle
- Create `tests/integration/test_job_lifecycle.py`
- Test complete flow: place job in queue → grab → execute → complete
- Test control queue priority over common queue
- Test concurrent job execution by same grabber (sequential processing)
- Test that spool directory contains jobs in various states
- Test that log files are created with correct content
- Verify cleanup of completed jobs (DONE, FAILED, TIMEOUT states)

### 9. Write integration tests for signal handling in running grabbers
- Create `tests/integration/test_signal_handling.py`
- Test SIGINT during job execution (graceful shutdown)
- Test SIGUSR2 pause/resume during active polling
- Test SIGUSR1 status dump (verify output format when implemented)
- Test signal handling with no active jobs
- Test lock file cleanup after SIGINT
- Verify that paused grabber resumes correctly after SIGUSR2

### 10. Write integration tests for multi-grabber scenarios
- Create `tests/integration/test_multi_grabber.py`
- Test multiple grabber instances with same cluster path but different names
- Test job distribution across multiple grabbers
- Test race condition handling (FileNotFoundError when job grabbed by another)
- Test that lock files prevent duplicate grabber names
- Test control queue routing to specific grabber
- Verify no job is executed twice by different grabbers

### 11. Write end-to-end tests for distributed scenarios
- Create `tests/e2e/test_distributed_scenario.py`
- Test complete distributed workflow with multiple grabbers and job types
- Simulate realistic cluster environment with:
  - 3+ grabber instances
  - Mix of control queue and common queue jobs
  - Jobs with different durations and exit codes
  - Signal-based control (pause/resume/shutdown)
- Verify all jobs are executed exactly once
- Verify correct final state of all jobs (DONE/FAILED/TIMEOUT)
- Validate log files contain complete execution history
- Test cleanup and graceful shutdown of all grabbers

### 12. Add edge case and error condition tests
- Add edge case tests across appropriate test files:
  - Empty queue directories
  - Malformed job scripts (syntax errors)
  - Jobs that exceed timeout (when timeout is implemented)
  - Stale lock files from crashed grabbers
  - Disk space exhaustion scenarios (mock)
  - Permission errors on spool/queue directories
  - Very long job names (path length limits)
  - Jobs that modify their own files
  - Concurrent access to same directories

### 13. Configure test coverage and reporting
- Add coverage configuration to `pyproject.toml`:
  - Minimum coverage threshold (aim for 80%+)
  - Coverage report formats (terminal, HTML, XML)
  - Files to include/exclude from coverage
- Create test markers for different test types:
  - `@pytest.mark.unit` for unit tests
  - `@pytest.mark.integration` for integration tests
  - `@pytest.mark.e2e` for end-to-end tests
  - `@pytest.mark.slow` for long-running tests
- Add coverage reporting to validation commands

### 14. Update documentation with testing instructions
- Update `README.md` with "Testing" section:
  - How to install test dependencies: `uv pip install -e ".[dev]"`
  - How to run all tests: `uv run pytest`
  - How to run specific test types: `uv run pytest -m unit`
  - How to generate coverage report: `uv run pytest --cov`
  - How to run tests with verbose output: `uv run pytest -v`
- Update `CLAUDE.md` with testing best practices:
  - Test file organization and naming conventions
  - Fixture usage and shared utilities
  - Running tests during development
  - Debugging failed tests
  - Adding new test cases

### 15. Run all validation commands
- Execute all validation commands to ensure zero regressions
- Fix any issues discovered during validation
- Ensure all tests pass and coverage meets minimum threshold
- Verify documentation is accurate and complete

## Validation Commands
Execute every command to validate the chore is complete with zero regressions.

- `uv pip install -e ".[dev]"` - Install package with test dependencies
- `uv run pytest -v` - Run all tests with verbose output, verify all pass
- `uv run pytest -m unit -v` - Run only unit tests, verify all pass
- `uv run pytest -m integration -v` - Run only integration tests, verify all pass
- `uv run pytest -m e2e -v` - Run only end-to-end tests, verify all pass
- `uv run pytest --cov=src/script_grabber --cov-report=term-missing` - Generate coverage report, verify ≥80% coverage
- `uv run pytest --cov=src/script_grabber --cov-report=html` - Generate HTML coverage report for review
- `uv run pytest tests/unit/test_exceptions.py -v` - Verify exception tests pass
- `uv run pytest tests/unit/test_grabber.py -v` - Verify Grabber unit tests pass
- `uv run pytest tests/integration/ -v` - Verify integration tests pass
- `uv run pytest tests/e2e/ -v` - Verify end-to-end tests pass
- `uv run pytest -k "signal" -v` - Run all signal-related tests
- `uv run pytest -k "multi_grabber" -v` - Run multi-grabber scenario tests
- `python -m pytest --collect-only` - Verify test discovery finds all test files

## Notes

### Known Issues to Test
The test suite should specifically validate and document these known issues from the codebase:
1. **Line 150 bug**: `GrabLockError` is raised but doesn't prevent execution - test should verify this bug and document expected vs actual behavior
2. **Timeout not enforced**: job_timeout parameter exists but timeout is never enforced - tests should document this limitation
3. **Duplicate imports**: `time` module imported twice (lines 21, 30) - tests should work regardless
4. **GrabError duplication**: Exception defined in both `grabber.py` and `grabexceptions.py` - tests should use the one from `grabexceptions.py`
5. **SIGUSR1 incomplete**: Status dump is incomplete - tests should verify current behavior and be ready for future implementation

### Test Organization Strategy
- **Unit tests**: Fast, isolated, no file system dependencies (use mocking)
- **Integration tests**: Test real file system operations with temporary directories
- **E2E tests**: Full system tests with multiple processes, slower but comprehensive
- Use pytest markers to allow selective test execution during development

### Coverage Goals
- **Minimum**: 80% code coverage overall
- **Critical paths**: 100% coverage for job execution, signal handling, lock management
- **Exception handling**: All exception paths must be tested
- **Edge cases**: Cover error conditions and race scenarios

### Performance Considerations
- Integration and E2E tests will create temporary directories and spawn processes
- Use pytest-timeout to prevent hanging tests (default 30s for unit, 60s for integration, 120s for e2e)
- Clean up temporary files and processes in fixtures/teardown
- Consider parallel test execution with pytest-xdist for faster CI/CD

### Future Enhancements
- Add property-based testing with hypothesis for job name generation
- Add mutation testing with mutmut to verify test quality
- Add performance benchmarks for job throughput
- Consider adding contract tests for file system interface
- Add Docker-based E2E tests to verify containerized deployment
