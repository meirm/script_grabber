"""Pytest configuration and shared fixtures for ScriptGrabber tests."""

import os
import sys
import tempfile
import shutil
from pathlib import Path
from typing import Generator
import pytest

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from script_grabber.grabber import Grabber
from tests.fixtures import sample_jobs


@pytest.fixture
def temp_cluster_path(tmp_path) -> Generator[Path, None, None]:
    """Create a temporary cluster directory structure.

    Creates:
    - queue/ (common queue)
    - ctrl/<name>/ (control queues, created per grabber)
    - spool/<name>/ (spool directories, created per grabber)
    - log/ (log directory)
    - varlock/ (lock file directory)
    """
    cluster_path = tmp_path / "cluster"
    cluster_path.mkdir()

    # Create base directories
    (cluster_path / "queue").mkdir()
    (cluster_path / "ctrl").mkdir()
    (cluster_path / "spool").mkdir()
    (cluster_path / "log").mkdir()
    (cluster_path / "varlock").mkdir()

    yield cluster_path

    # Cleanup is automatic with tmp_path


@pytest.fixture
def sample_grabber(temp_cluster_path) -> Grabber:
    """Create a pre-configured Grabber instance for testing.

    Note: Does not call run(), just creates the instance.
    Signal handlers are registered during __init__.
    """
    grabber = Grabber(
        name="test_grabber",
        clusterpath=str(temp_cluster_path),
        job_timeout=60,
    )
    return grabber


@pytest.fixture
def second_grabber(temp_cluster_path) -> Grabber:
    """Create a second Grabber instance for multi-grabber tests."""
    grabber = Grabber(
        name="test_grabber_2",
        clusterpath=str(temp_cluster_path),
        job_timeout=60,
    )
    return grabber


@pytest.fixture
def mock_job_success(temp_cluster_path) -> Path:
    """Create a sample job script that succeeds (exit code 0)."""
    job_path = temp_cluster_path / "queue" / "success_job.py"
    job_path.write_text(sample_jobs.SUCCESS_JOB)
    return job_path


@pytest.fixture
def mock_job_failure(temp_cluster_path) -> Path:
    """Create a sample job script that fails (exit code 1)."""
    job_path = temp_cluster_path / "queue" / "failure_job.py"
    job_path.write_text(sample_jobs.FAILURE_JOB)
    return job_path


@pytest.fixture
def mock_job_timeout(temp_cluster_path) -> Path:
    """Create a sample job script that simulates timeout (exit code 124)."""
    job_path = temp_cluster_path / "queue" / "timeout_job.py"
    job_path.write_text(sample_jobs.TIMEOUT_JOB)
    return job_path


@pytest.fixture
def mock_job_long_running(temp_cluster_path) -> Path:
    """Create a sample job script that runs for a long time."""
    job_path = temp_cluster_path / "queue" / "long_running_job.py"
    job_path.write_text(sample_jobs.LONG_RUNNING_JOB)
    return job_path


@pytest.fixture
def mock_job_output(temp_cluster_path) -> Path:
    """Create a sample job script that writes to stdout and stderr."""
    job_path = temp_cluster_path / "queue" / "output_job.py"
    job_path.write_text(sample_jobs.OUTPUT_JOB)
    return job_path


@pytest.fixture
def mock_job_env(temp_cluster_path) -> Path:
    """Create a sample job script that uses environment variables."""
    job_path = temp_cluster_path / "queue" / "env_job.py"
    job_path.write_text(sample_jobs.ENV_JOB)
    return job_path


@pytest.fixture
def cleanup_locks(temp_cluster_path):
    """Fixture to clean up lock files after tests."""
    yield
    # Cleanup lock files
    varlock_dir = temp_cluster_path / "varlock"
    if varlock_dir.exists():
        for lock_file in varlock_dir.glob("*.lock"):
            try:
                lock_file.unlink()
            except FileNotFoundError:
                pass


@pytest.fixture
def ctrl_queue_job(temp_cluster_path, sample_grabber) -> Path:
    """Create a job in the control queue for a specific grabber."""
    ctrl_queue = Path(sample_grabber.ctrlqueue)
    ctrl_queue.mkdir(parents=True, exist_ok=True)
    job_path = ctrl_queue / "ctrl_job.py"
    job_path.write_text(sample_jobs.SUCCESS_JOB)
    return job_path


@pytest.fixture
def multiple_jobs(temp_cluster_path) -> list[Path]:
    """Create multiple jobs in the common queue."""
    jobs = []
    for i in range(5):
        job_path = temp_cluster_path / "queue" / f"job_{i}.py"
        job_path.write_text(sample_jobs.SUCCESS_JOB)
        jobs.append(job_path)
    return jobs
