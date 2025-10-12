"""Integration tests for complete job lifecycle."""

import os
import time
from pathlib import Path
import pytest

from script_grabber.grabber import Grabber


@pytest.mark.integration
class TestJobLifecycle:
    """Test complete job lifecycle: queued → grabbed → running → completed."""

    def test_complete_success_lifecycle(self, temp_cluster_path, mock_job_success):
        """Test complete flow for successful job."""
        grabber = Grabber("test_grabber", str(temp_cluster_path))

        # Job starts in queue
        assert mock_job_success.exists()

        # Grab and run the job
        job_path = grabber.grab_job()
        assert job_path is not None
        assert "-RUNNING" in job_path

        grabber.running_job_path = job_path
        grabber.run_job()

        # Job should now be marked as DONE
        done_path = job_path.replace("-RUNNING", "-DONE")
        assert Path(done_path).exists()

        # Log files should exist
        log_file = Path(grabber.spoollog) / f"{grabber.job_file}.log"
        out_file = Path(grabber.spoollog) / f"{grabber.job_file}.out"
        err_file = Path(grabber.spoollog) / f"{grabber.job_file}.err"

        assert log_file.exists()
        assert out_file.exists()
        assert err_file.exists()

    def test_complete_failure_lifecycle(self, temp_cluster_path, mock_job_failure):
        """Test complete flow for failed job."""
        grabber = Grabber("test_grabber", str(temp_cluster_path))

        job_path = grabber.grab_job()
        grabber.running_job_path = job_path
        grabber.run_job()

        # Job should be marked as FAILED
        failed_path = job_path.replace("-RUNNING", "-FAILED")
        assert Path(failed_path).exists()

        # Check error output
        err_file = Path(grabber.spoollog) / f"{grabber.job_file}.err"
        assert err_file.exists()
        content = err_file.read_text()
        assert "ERROR" in content

    def test_control_queue_priority(
        self, temp_cluster_path, ctrl_queue_job, mock_job_success
    ):
        """Test that control queue has priority over common queue."""
        grabber = Grabber("test_grabber", str(temp_cluster_path))

        # Grab job - should get control queue job first
        job_path = grabber.grab_job()
        assert "ctrl_job" in job_path

        # Execute it
        grabber.running_job_path = job_path
        grabber.run_job()

        # Now grab again - should get common queue job
        job_path = grabber.grab_job()
        assert "success_job" in job_path

    def test_sequential_job_processing(self, temp_cluster_path, multiple_jobs):
        """Test sequential processing of multiple jobs."""
        grabber = Grabber("test_grabber", str(temp_cluster_path))

        completed_jobs = []

        # Process all jobs
        for _ in range(len(multiple_jobs)):
            job_path = grabber.grab_job()
            if job_path:
                grabber.running_job_path = job_path
                grabber.run_job()
                completed_jobs.append(job_path)

        # All jobs should be processed
        assert len(completed_jobs) == len(multiple_jobs)

        # All jobs should be marked as DONE
        spool_dir = Path(grabber.spool)
        done_jobs = list(spool_dir.glob("*-DONE"))
        assert len(done_jobs) == len(multiple_jobs)

    def test_spool_directory_states(self, temp_cluster_path, multiple_jobs):
        """Test that spool directory contains jobs in various states."""
        grabber = Grabber("test_grabber", str(temp_cluster_path))

        # Grab but don't run first job (stays in RUNNING state)
        job1_path = grabber.grab_job()
        assert "-RUNNING" in job1_path

        # Grab and run second job
        job2_path = grabber.grab_job()
        grabber.running_job_path = job2_path
        grabber.run_job()

        # Check spool states
        spool_dir = Path(grabber.spool)
        running_jobs = list(spool_dir.glob("*-RUNNING"))
        done_jobs = list(spool_dir.glob("*-DONE"))

        assert len(running_jobs) == 1
        assert len(done_jobs) == 1


@pytest.mark.integration
class TestLogFileCreation:
    """Test log file creation and content."""

    def test_log_file_contains_job_info(self, temp_cluster_path, mock_job_success):
        """Test that log file contains job name, timestamp, and exit code."""
        grabber = Grabber("test_grabber", str(temp_cluster_path))

        job_path = grabber.grab_job()
        grabber.running_job_path = job_path
        grabber.run_job()

        log_file = Path(grabber.spoollog) / f"{grabber.job_file}.log"
        content = log_file.read_text()

        assert grabber.job_file in content
        assert "ExitCode(0)" in content
        # Check timestamp format (YYYYMMDDHHMMSS)
        import re

        assert re.search(r"\d{14}", content)

    def test_stdout_capture_complete(self, temp_cluster_path, mock_job_output):
        """Test that all stdout is captured correctly."""
        grabber = Grabber("test_grabber", str(temp_cluster_path))

        job_path = grabber.grab_job()
        grabber.running_job_path = job_path
        grabber.run_job()

        out_file = Path(grabber.spoollog) / f"{grabber.job_file}.out"
        content = out_file.read_text()

        assert "Line 1 to stdout" in content
        assert "Line 2 to stdout" in content
        assert "Line 3 to stdout" in content

    def test_stderr_capture_complete(self, temp_cluster_path, mock_job_output):
        """Test that all stderr is captured correctly."""
        grabber = Grabber("test_grabber", str(temp_cluster_path))

        job_path = grabber.grab_job()
        grabber.running_job_path = job_path
        grabber.run_job()

        err_file = Path(grabber.spoollog) / f"{grabber.job_file}.err"
        content = err_file.read_text()

        assert "Line 1 to stderr" in content
        assert "Line 2 to stderr" in content

    def test_log_files_for_failed_jobs(self, temp_cluster_path, mock_job_failure):
        """Test that log files are created even for failed jobs."""
        grabber = Grabber("test_grabber", str(temp_cluster_path))

        job_path = grabber.grab_job()
        grabber.running_job_path = job_path
        grabber.run_job()

        log_file = Path(grabber.spoollog) / f"{grabber.job_file}.log"
        out_file = Path(grabber.spoollog) / f"{grabber.job_file}.out"
        err_file = Path(grabber.spoollog) / f"{grabber.job_file}.err"

        assert log_file.exists()
        assert out_file.exists()
        assert err_file.exists()

        # Check exit code in log
        log_content = log_file.read_text()
        assert "ExitCode(1)" in log_content


@pytest.mark.integration
@pytest.mark.timeout(60)
class TestEmptyQueueBehavior:
    """Test behavior when queues are empty."""

    def test_grab_from_empty_queue(self, temp_cluster_path):
        """Test that grab_job() returns None when queues are empty."""
        grabber = Grabber("test_grabber", str(temp_cluster_path))

        job_path = grabber.grab_job()
        assert job_path is None

    def test_multiple_grabs_from_empty_queue(self, temp_cluster_path):
        """Test that multiple grab attempts on empty queue all return None."""
        grabber = Grabber("test_grabber", str(temp_cluster_path))

        for _ in range(5):
            job_path = grabber.grab_job()
            assert job_path is None
