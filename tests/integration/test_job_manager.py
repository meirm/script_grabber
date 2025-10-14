"""Integration tests for JobManager with bash script execution."""

import pytest
from pathlib import Path
import tempfile
import shutil
import sys
import os

# Add apps/backend to path to import job_manager
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "apps" / "backend"))

from script_grabber.grabber import Grabber
from core.job_manager import JobManager


@pytest.fixture
def temp_cluster():
    """Create a temporary cluster directory structure."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cluster_path = Path(tmpdir)
        # Create directory structure
        (cluster_path / "queue").mkdir()
        (cluster_path / "spool" / "test_grabber").mkdir(parents=True)
        (cluster_path / "log").mkdir()
        (cluster_path / "varlock").mkdir()
        (cluster_path / "ctrl" / "test_grabber").mkdir(parents=True)
        yield cluster_path


@pytest.fixture
def job_manager(temp_cluster):
    """Create a JobManager instance for testing."""
    return JobManager(str(temp_cluster))


@pytest.fixture
def grabber(temp_cluster):
    """Create a Grabber instance for testing."""
    return Grabber(name="test_grabber", clusterpath=str(temp_cluster))


@pytest.mark.integration
class TestJobManagerWithBashScripts:
    """Test JobManager integration with bash script execution."""

    @pytest.mark.asyncio
    async def test_bash_script_exit_code_success(self, job_manager, grabber, temp_cluster):
        """Test that JobManager correctly retrieves exit code for successful bash script."""
        # Submit a bash script through JobManager
        script_content = b"#!/bin/bash\necho 'Success'\nexit 0\n"
        job_id = await job_manager.submit_job("test_script.sh", script_content)

        # Verify job is queued
        status = await job_manager.get_job_status(job_id)
        assert status.status == "queued"
        assert status.job_id == job_id

        # Grab and execute the job
        job_path = grabber.grab_job()
        assert job_path is not None
        grabber.running_job_path = job_path
        grabber.run_job()

        # Get job status after execution
        status = await job_manager.get_job_status(job_id)

        # Verify job completed successfully
        assert status.status == "done"
        assert status.exit_code == 0
        assert "Success" in status.stdout
        assert status.grabber == "test_grabber"

    @pytest.mark.asyncio
    async def test_bash_script_exit_code_failure(self, job_manager, grabber, temp_cluster):
        """Test that JobManager correctly retrieves exit code for failed bash script."""
        # Submit a bash script that fails
        script_content = b"#!/bin/bash\necho 'Failure'\nexit 1\n"
        job_id = await job_manager.submit_job("failing_script.sh", script_content)

        # Grab and execute the job
        job_path = grabber.grab_job()
        assert job_path is not None
        grabber.running_job_path = job_path
        grabber.run_job()

        # Get job status after execution
        status = await job_manager.get_job_status(job_id)

        # Verify job failed with correct exit code
        assert status.status == "failed"
        assert status.exit_code == 1
        assert "Failure" in status.stdout

    @pytest.mark.asyncio
    async def test_bash_script_exit_code_timeout(self, job_manager, grabber, temp_cluster):
        """Test that JobManager correctly handles timeout exit code (124)."""
        # Submit a bash script that simulates timeout
        script_content = b"#!/bin/bash\necho 'Timeout'\nexit 124\n"
        job_id = await job_manager.submit_job("timeout_script.sh", script_content)

        # Grab and execute the job
        job_path = grabber.grab_job()
        assert job_path is not None
        grabber.running_job_path = job_path
        grabber.run_job()

        # Get job status after execution
        status = await job_manager.get_job_status(job_id)

        # Verify job marked as timeout with correct exit code
        assert status.status == "timeout"
        assert status.exit_code == 124
        assert "Timeout" in status.stdout

    @pytest.mark.asyncio
    async def test_python_script_exit_code(self, job_manager, grabber, temp_cluster):
        """Test that JobManager works with Python scripts too (backward compatibility)."""
        # Submit a Python script
        script_content = b"#!/usr/bin/env python3\nprint('Python works')\nexit(42)\n"
        job_id = await job_manager.submit_job("test_script.py", script_content)

        # Grab and execute the job
        job_path = grabber.grab_job()
        assert job_path is not None
        grabber.running_job_path = job_path
        grabber.run_job()

        # Get job status after execution
        status = await job_manager.get_job_status(job_id)

        # Verify job failed with correct exit code
        assert status.status == "failed"
        assert status.exit_code == 42
        assert "Python works" in status.stdout

    @pytest.mark.asyncio
    async def test_complex_filename_with_extension(self, job_manager, grabber, temp_cluster):
        """Test that log files are correctly found for jobs with complex filenames."""
        # This specifically tests the bug fix where job_id includes extension and timestamp
        # Job ID format: script.sh_20251014_061639_364612
        script_content = b"#!/bin/bash\necho 'Complex filename test'\nexit 7\n"
        job_id = await job_manager.submit_job("hello_world.sh", script_content)

        # Verify job_id includes the extension
        assert ".sh" in job_id
        assert "_" in job_id  # Should have timestamp

        # Grab and execute the job
        job_path = grabber.grab_job()
        assert job_path is not None
        grabber.running_job_path = job_path
        grabber.run_job()

        # Get job status - this is where the bug would manifest
        status = await job_manager.get_job_status(job_id)

        # Verify exit code is found (not None/"N/A")
        assert status.exit_code is not None
        assert status.exit_code == 7
        assert status.status == "failed"
        assert "Complex filename test" in status.stdout

    @pytest.mark.asyncio
    async def test_stderr_capture(self, job_manager, grabber, temp_cluster):
        """Test that stderr is correctly captured and retrieved."""
        script_content = b"#!/bin/bash\necho 'stdout message'\necho 'stderr message' >&2\nexit 5\n"
        job_id = await job_manager.submit_job("stderr_test.sh", script_content)

        # Grab and execute the job
        job_path = grabber.grab_job()
        grabber.running_job_path = job_path
        grabber.run_job()

        # Get job status
        status = await job_manager.get_job_status(job_id)

        # Verify both stdout and stderr are captured
        assert status.exit_code == 5
        assert "stdout message" in status.stdout
        assert "stderr message" in status.stderr
