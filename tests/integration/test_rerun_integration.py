#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Integration tests for the rerun functionality in the ScriptGrabber system.

These tests verify the complete rerun workflow with real file system operations.
"""

import os
import sys
import time
import pytest
import subprocess
from pathlib import Path

from script_grabber.grabber import Grabber
from script_grabber.grabexceptions import GrabTaskNotFoundError, GrabRerunError


@pytest.fixture
def completed_done_job(temp_cluster_path):
    """
    Fixture that creates and runs a job to DONE state.
    Returns (grabber, job_name).
    """
    grabber = Grabber("test_grabber", temp_cluster_path)

    # Create a simple job that succeeds
    job_name = "success_job.py"
    job_path = os.path.join(grabber.queue, job_name)

    with open(job_path, "w") as f:
        f.write("#!/usr/bin/env python3\n")
        f.write("print('Job executed successfully')\n")
        f.write("exit(0)\n")

    # Execute one iteration to grab and run the job
    grabber.running_job_path = grabber.grab_job()
    if grabber.running_job_path:
        grabber.run_job()

    return grabber, job_name


@pytest.fixture
def completed_failed_job(temp_cluster_path):
    """
    Fixture that creates and runs a job to FAILED state.
    Returns (grabber, job_name).
    """
    grabber = Grabber("test_grabber", temp_cluster_path)

    # Create a job that fails
    job_name = "failed_job.py"
    job_path = os.path.join(grabber.queue, job_name)

    with open(job_path, "w") as f:
        f.write("#!/usr/bin/env python3\n")
        f.write("print('Job failed')\n")
        f.write("exit(1)\n")

    # Execute one iteration
    grabber.running_job_path = grabber.grab_job()
    if grabber.running_job_path:
        grabber.run_job()

    return grabber, job_name


@pytest.fixture
def completed_timeout_job(temp_cluster_path):
    """
    Fixture that creates and runs a job to TIMEOUT state.
    Returns (grabber, job_name).
    """
    grabber = Grabber("test_grabber", temp_cluster_path)

    # Create a job that simulates timeout (exit code 124)
    job_name = "timeout_job.py"
    job_path = os.path.join(grabber.queue, job_name)

    with open(job_path, "w") as f:
        f.write("#!/usr/bin/env python3\n")
        f.write("print('Job timed out')\n")
        f.write("exit(124)\n")

    # Execute one iteration
    grabber.running_job_path = grabber.grab_job()
    if grabber.running_job_path:
        grabber.run_job()

    return grabber, job_name


@pytest.mark.integration
class TestRerunIntegration:
    """Integration tests for complete rerun workflows."""

    def test_rerun_done_job_end_to_end(self, completed_done_job):
        """Test complete workflow: create → run → complete → rerun → verify."""
        grabber, job_name = completed_done_job

        # Verify job completed successfully (DONE state)
        spool_files = os.listdir(grabber.spool)
        done_files = [f for f in spool_files if f.endswith('-DONE')]
        assert len(done_files) == 1
        assert done_files[0].startswith(job_name.replace('.py', ''))

        # Rerun the job
        result = grabber.rerun_task(job_name, "common")

        # Verify job was placed in queue
        assert os.path.exists(result)
        assert result == os.path.join(grabber.queue, job_name)

        # Verify original DONE job is still in spool
        assert len([f for f in os.listdir(grabber.spool) if f.endswith('-DONE')]) == 1

        # Sleep to ensure different timestamps (timestamp resolution is 1 second)
        time.sleep(1.1)

        # Verify job is actually in the queue before grabbing
        queue_files = os.listdir(grabber.queue)
        assert job_name in queue_files, f"Job {job_name} not found in queue. Queue contains: {queue_files}"

        # Execute the rerun job
        grabber.running_job_path = grabber.grab_job()
        assert grabber.running_job_path is not None, f"Failed to grab job from queue. Queue: {os.listdir(grabber.queue)}, Ctrl: {os.listdir(grabber.ctrlqueue)}"
        grabber.run_job()

        # Verify second execution completed
        spool_files = os.listdir(grabber.spool)
        done_files = [f for f in spool_files if f.endswith('-DONE')]
        assert len(done_files) == 2, f"Expected 2 DONE files but got {len(done_files)}. Spool contents: {spool_files}"

    def test_rerun_failed_job_with_fix(self, temp_cluster_path):
        """Test rerunning a failed job that can succeed on retry."""
        grabber = Grabber("test_grabber", temp_cluster_path)

        # Create a job that fails initially
        job_name = "conditional_job.py"
        job_path = os.path.join(grabber.queue, job_name)

        with open(job_path, "w") as f:
            f.write("#!/usr/bin/env python3\n")
            f.write("import os\n")
            f.write("flag_file = '/tmp/test_flag.txt'\n")
            f.write("if os.path.exists(flag_file):\n")
            f.write("    print('Success on retry')\n")
            f.write("    exit(0)\n")
            f.write("else:\n")
            f.write("    print('Failed first time')\n")
            f.write("    exit(1)\n")

        # First execution (should fail)
        grabber.running_job_path = grabber.grab_job()
        if grabber.running_job_path:
            grabber.run_job()

        # Verify failed
        failed_files = [f for f in os.listdir(grabber.spool) if f.endswith('-FAILED')]
        assert len(failed_files) == 1

        # Create flag file to make job succeed on retry
        with open('/tmp/test_flag.txt', 'w') as f:
            f.write('flag')

        # Rerun the job
        result = grabber.rerun_task(job_name, "common")
        assert os.path.exists(result)

        # Second execution (should succeed)
        grabber.running_job_path = grabber.grab_job()
        if grabber.running_job_path:
            grabber.run_job()

        # Verify succeeded
        done_files = [f for f in os.listdir(grabber.spool) if f.endswith('-DONE')]
        assert len(done_files) == 1

        # Cleanup
        if os.path.exists('/tmp/test_flag.txt'):
            os.remove('/tmp/test_flag.txt')

    def test_rerun_preserves_job_history(self, completed_done_job):
        """Test that rerun preserves original job in spool directory."""
        grabber, job_name = completed_done_job

        # Get original job details
        spool_files = os.listdir(grabber.spool)
        original_done_files = [f for f in spool_files if f.endswith('-DONE')]
        assert len(original_done_files) == 1
        original_job_path = os.path.join(grabber.spool, original_done_files[0])

        # Read original job content
        with open(original_job_path, 'r') as f:
            original_content = f.read()

        # Rerun the job
        grabber.rerun_task(job_name, "common")

        # Verify original job is still there with same content
        assert os.path.exists(original_job_path)
        with open(original_job_path, 'r') as f:
            current_content = f.read()
        assert current_content == original_content

    def test_rerun_to_control_queue(self, completed_done_job):
        """Test rerunning job to control queue instead of common queue."""
        grabber, job_name = completed_done_job

        # Rerun to control queue
        result = grabber.rerun_task(job_name, "control")

        # Verify job was placed in control queue
        assert result == os.path.join(grabber.ctrlqueue, job_name)
        assert os.path.exists(result)

        # Verify NOT in common queue
        common_queue_path = os.path.join(grabber.queue, job_name)
        assert not os.path.exists(common_queue_path)

    def test_rerun_multiple_times(self, completed_done_job):
        """Test that the same job can be rerun multiple times."""
        grabber, job_name = completed_done_job

        # First rerun
        time.sleep(1.1)  # Ensure different timestamp
        result1 = grabber.rerun_task(job_name, "common")
        assert os.path.exists(result1)

        # Execute first rerun
        time.sleep(1.1)  # Ensure different timestamp
        grabber.running_job_path = grabber.grab_job()
        if grabber.running_job_path:
            grabber.run_job()

        # Second rerun
        time.sleep(1.1)  # Ensure different timestamp
        result2 = grabber.rerun_task(job_name, "common")
        assert os.path.exists(result2)

        # Execute second rerun
        time.sleep(1.1)  # Ensure different timestamp
        grabber.running_job_path = grabber.grab_job()
        if grabber.running_job_path:
            grabber.run_job()

        # Verify we have 3 DONE jobs total (original + 2 reruns)
        done_files = [f for f in os.listdir(grabber.spool) if f.endswith('-DONE')]
        assert len(done_files) == 3, f"Expected 3 DONE files but got {len(done_files)}. Spool contents: {os.listdir(grabber.spool)}"

    def test_rerun_nonexistent_job_error(self, temp_cluster_path):
        """Test that rerunning nonexistent job raises proper error."""
        grabber = Grabber("test_grabber", temp_cluster_path)

        with pytest.raises(GrabTaskNotFoundError) as exc_info:
            grabber.rerun_task("nonexistent.py", "common")

        assert "not found" in str(exc_info.value.message).lower()

    def test_rerun_failed_job(self, completed_failed_job):
        """Test rerunning a FAILED job."""
        grabber, job_name = completed_failed_job

        # Verify job failed
        failed_files = [f for f in os.listdir(grabber.spool) if f.endswith('-FAILED')]
        assert len(failed_files) == 1

        # Rerun the failed job
        result = grabber.rerun_task(job_name, "common")
        assert os.path.exists(result)

        # Verify original failed job is still in spool
        assert len([f for f in os.listdir(grabber.spool) if f.endswith('-FAILED')]) == 1

    def test_rerun_timeout_job(self, completed_timeout_job):
        """Test rerunning a TIMEOUT job."""
        grabber, job_name = completed_timeout_job

        # Verify job timed out
        timeout_files = [f for f in os.listdir(grabber.spool) if f.endswith('-TIMEOUT')]
        assert len(timeout_files) == 1

        # Rerun the timeout job
        result = grabber.rerun_task(job_name, "common")
        assert os.path.exists(result)

        # Verify original timeout job is still in spool
        assert len([f for f in os.listdir(grabber.spool) if f.endswith('-TIMEOUT')]) == 1


@pytest.mark.integration
class TestRerunCLI:
    """Integration tests for the grabber-rerun CLI command."""

    def test_cli_rerun_success(self, completed_done_job):
        """Test successful CLI execution."""
        grabber, job_name = completed_done_job

        # Run CLI command
        result = subprocess.run(
            [sys.executable, "-m", "script_grabber.rerun",
             "test_grabber", grabber.clusterpath, job_name],
            capture_output=True,
            text=True
        )

        # Verify success
        assert result.returncode == 0
        assert "Successfully requeued" in result.stdout
        assert job_name in result.stdout

        # Verify job is in queue
        queue_path = os.path.join(grabber.queue, job_name)
        assert os.path.exists(queue_path)

    def test_cli_rerun_nonexistent_job(self, temp_cluster_path):
        """Test CLI error handling for nonexistent job."""
        # Run CLI command with nonexistent job
        result = subprocess.run(
            [sys.executable, "-m", "script_grabber.rerun",
             "test_grabber", temp_cluster_path, "nonexistent.py"],
            capture_output=True,
            text=True
        )

        # Verify error
        assert result.returncode == 1
        assert "not found" in result.stderr.lower()

    def test_cli_rerun_with_queue_type_flag(self, completed_done_job):
        """Test CLI with --queue-type parameter."""
        grabber, job_name = completed_done_job

        # Run CLI command with control queue
        result = subprocess.run(
            [sys.executable, "-m", "script_grabber.rerun",
             "test_grabber", grabber.clusterpath, job_name,
             "--queue-type", "control"],
            capture_output=True,
            text=True
        )

        # Verify success
        assert result.returncode == 0
        assert "control" in result.stdout

        # Verify job is in control queue
        ctrl_queue_path = os.path.join(grabber.ctrlqueue, job_name)
        assert os.path.exists(ctrl_queue_path)

    def test_cli_rerun_exit_codes(self, completed_done_job, temp_cluster_path):
        """Test CLI exit codes for success and error cases."""
        grabber, job_name = completed_done_job

        # Test success case (exit 0)
        result_success = subprocess.run(
            [sys.executable, "-m", "script_grabber.rerun",
             "test_grabber", grabber.clusterpath, job_name],
            capture_output=True
        )
        assert result_success.returncode == 0

        # Test error case (exit 1)
        result_error = subprocess.run(
            [sys.executable, "-m", "script_grabber.rerun",
             "test_grabber", temp_cluster_path, "nonexistent.py"],
            capture_output=True
        )
        assert result_error.returncode == 1

    def test_cli_help_message(self):
        """Test that CLI help message is accessible."""
        result = subprocess.run(
            [sys.executable, "-m", "script_grabber.rerun", "--help"],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0
        assert "grabber-rerun" in result.stdout or "rerun" in result.stdout
        assert "grabber_name" in result.stdout
        assert "cluster_path" in result.stdout
        assert "job_name" in result.stdout
        assert "--queue-type" in result.stdout
