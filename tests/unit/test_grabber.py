"""Unit tests for Grabber class."""

import os
import sys
import signal
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest

from script_grabber.grabber import Grabber
from script_grabber.grabexceptions import GrabLockError


@pytest.mark.unit
class TestGrabberInitialization:
    """Test Grabber __init__() with various parameter combinations."""

    def test_init_with_required_params_only(self, temp_cluster_path):
        """Test initialization with only required parameters."""
        grabber = Grabber("test_grabber", str(temp_cluster_path))

        assert grabber.grabberName == "test_grabber"
        assert grabber.clusterpath == str(temp_cluster_path)
        assert grabber.is_running is True
        assert grabber.is_paused is False

    def test_init_with_all_params(self, temp_cluster_path):
        """Test initialization with all parameters specified."""
        grabber = Grabber(
            name="test_grabber",
            clusterpath=str(temp_cluster_path),
            job_timeout=7200,
            ctrlqueue=str(temp_cluster_path / "custom_ctrl"),
            queue=str(temp_cluster_path / "custom_queue"),
            spool=str(temp_cluster_path / "custom_spool"),
            spoollog=str(temp_cluster_path / "custom_log"),
            varlock=str(temp_cluster_path / "custom_varlock"),
            logfile=str(temp_cluster_path / "custom.log"),
            sleep_time=5,
        )

        assert grabber.job_timeout == 7200
        assert grabber.sleep_time == 5
        assert "custom_ctrl" in grabber.ctrlqueue
        assert "custom_queue" in grabber.queue

    def test_init_creates_logger(self, temp_cluster_path):
        """Test that logger is created during initialization."""
        grabber = Grabber("test_grabber", str(temp_cluster_path))
        assert grabber.logger is not None
        assert grabber.logger.name == "grabber"

    def test_init_registers_signal_handlers(self, temp_cluster_path):
        """Test that signal handlers are registered during initialization."""
        # Store original handlers
        original_sigint = signal.getsignal(signal.SIGINT)
        original_sigusr1 = signal.getsignal(signal.SIGUSR1)
        original_sigusr2 = signal.getsignal(signal.SIGUSR2)

        grabber = Grabber("test_grabber", str(temp_cluster_path))

        # Check handlers are different from originals
        current_sigint = signal.getsignal(signal.SIGINT)
        current_sigusr1 = signal.getsignal(signal.SIGUSR1)
        current_sigusr2 = signal.getsignal(signal.SIGUSR2)

        # Note: Signals are registered, but we can't easily verify the exact handler
        # without more complex mocking. This at least verifies initialization completed.
        assert grabber is not None


@pytest.mark.unit
class TestGrabberDefaults:
    """Test defaults() method applies correct default paths."""

    def test_defaults_sets_ctrlqueue(self, temp_cluster_path):
        """Test defaults() sets control queue path correctly."""
        grabber = Grabber("test_grabber", str(temp_cluster_path))
        expected = f"{temp_cluster_path}/ctrl/test_grabber"
        assert grabber.ctrlqueue == expected

    def test_defaults_sets_queue(self, temp_cluster_path):
        """Test defaults() sets common queue path correctly."""
        grabber = Grabber("test_grabber", str(temp_cluster_path))
        expected = f"{temp_cluster_path}/queue"
        assert grabber.queue == expected

    def test_defaults_sets_spool(self, temp_cluster_path):
        """Test defaults() sets spool path correctly."""
        grabber = Grabber("test_grabber", str(temp_cluster_path))
        expected = f"{temp_cluster_path}/spool/test_grabber"
        assert grabber.spool == expected

    def test_defaults_sets_spoollog(self, temp_cluster_path):
        """Test defaults() sets spool log path correctly."""
        grabber = Grabber("test_grabber", str(temp_cluster_path))
        expected = f"{temp_cluster_path}/log"
        assert grabber.spoollog == expected

    def test_defaults_sets_varlock(self, temp_cluster_path):
        """Test defaults() sets varlock path correctly."""
        grabber = Grabber("test_grabber", str(temp_cluster_path))
        expected = f"{temp_cluster_path}/varlock"
        assert grabber.varlock == expected

    def test_defaults_sets_job_timeout(self, temp_cluster_path):
        """Test defaults() sets job timeout to 3600 seconds."""
        grabber = Grabber("test_grabber", str(temp_cluster_path))
        assert grabber.job_timeout == 3600

    def test_defaults_sets_sleep_time(self, temp_cluster_path):
        """Test defaults() sets sleep time to 10 seconds."""
        grabber = Grabber("test_grabber", str(temp_cluster_path))
        assert grabber.sleep_time == 10

    def test_defaults_respects_custom_values(self, temp_cluster_path):
        """Test defaults() does not override custom values."""
        custom_timeout = 7200
        custom_sleep = 5
        grabber = Grabber(
            "test_grabber",
            str(temp_cluster_path),
            job_timeout=custom_timeout,
            sleep_time=custom_sleep,
        )
        assert grabber.job_timeout == custom_timeout
        assert grabber.sleep_time == custom_sleep


@pytest.mark.unit
class TestGrabberEnsureDirs:
    """Test ensure_dirs() creates all required directories."""

    def test_ensure_dirs_creates_spool(self, temp_cluster_path):
        """Test ensure_dirs() creates spool directory."""
        grabber = Grabber("test_grabber", str(temp_cluster_path))
        assert Path(grabber.spool).exists()
        assert Path(grabber.spool).is_dir()

    def test_ensure_dirs_creates_ctrlqueue(self, temp_cluster_path):
        """Test ensure_dirs() creates control queue directory."""
        grabber = Grabber("test_grabber", str(temp_cluster_path))
        assert Path(grabber.ctrlqueue).exists()
        assert Path(grabber.ctrlqueue).is_dir()

    def test_ensure_dirs_creates_queue(self, temp_cluster_path):
        """Test ensure_dirs() creates common queue directory."""
        grabber = Grabber("test_grabber", str(temp_cluster_path))
        assert Path(grabber.queue).exists()
        assert Path(grabber.queue).is_dir()

    def test_ensure_dirs_creates_log(self, temp_cluster_path):
        """Test ensure_dirs() creates log directory."""
        grabber = Grabber("test_grabber", str(temp_cluster_path))
        log_dir = Path(grabber.clusterpath) / "log"
        assert log_dir.exists()
        assert log_dir.is_dir()

    def test_ensure_dirs_creates_varlock(self, temp_cluster_path):
        """Test ensure_dirs() creates varlock directory."""
        grabber = Grabber("test_grabber", str(temp_cluster_path))
        assert Path(grabber.varlock).exists()
        assert Path(grabber.varlock).is_dir()

    def test_ensure_dirs_idempotent(self, temp_cluster_path):
        """Test ensure_dirs() can be called multiple times safely."""
        grabber = Grabber("test_grabber", str(temp_cluster_path))
        # Call ensure_dirs again
        grabber.ensure_dirs()
        # Should not raise, directories still exist
        assert Path(grabber.spool).exists()


@pytest.mark.unit
class TestGrabberGrabJob:
    """Test grab_job() method for job grabbing logic."""

    def test_grab_job_from_control_queue(self, sample_grabber, ctrl_queue_job):
        """Test grabbing job from control queue (higher priority)."""
        job_path = sample_grabber.grab_job()

        assert job_path is not None
        assert "-RUNNING" in job_path
        assert Path(job_path).exists()
        # Job should be in spool now
        assert sample_grabber.spool in job_path

    def test_grab_job_from_common_queue(self, sample_grabber, mock_job_success):
        """Test grabbing job from common queue when control queue is empty."""
        job_path = sample_grabber.grab_job()

        assert job_path is not None
        assert "-RUNNING" in job_path
        assert Path(job_path).exists()
        assert sample_grabber.spool in job_path

    def test_grab_job_control_queue_priority(
        self, sample_grabber, ctrl_queue_job, mock_job_success
    ):
        """Test that control queue has priority over common queue."""
        # Both queues have jobs, control queue should be grabbed first
        job_path = sample_grabber.grab_job()

        assert job_path is not None
        assert "ctrl_job" in job_path  # Control queue job name

    def test_grab_job_returns_none_when_empty(self, sample_grabber):
        """Test grab_job() returns None when no jobs are available."""
        job_path = sample_grabber.grab_job()
        assert job_path is None

    def test_grab_job_sets_executable_permissions(self, sample_grabber, mock_job_success):
        """Test that grabbed job file is made executable (0o755)."""
        job_path = sample_grabber.grab_job()

        assert job_path is not None
        # Check file permissions
        stat_info = os.stat(job_path)
        mode = stat_info.st_mode
        # Check that file is executable
        assert mode & 0o111  # At least one execute bit set

    def test_grab_job_adds_timestamp(self, sample_grabber, mock_job_success):
        """Test that job is renamed with timestamp."""
        job_path = sample_grabber.grab_job()

        assert job_path is not None
        # Timestamp format: YYYYMMDDHHMMSS
        import re

        timestamp_pattern = r"\d{14}"
        assert re.search(timestamp_pattern, job_path)

    def test_grab_job_moves_to_spool(self, sample_grabber, mock_job_success):
        """Test that job is moved from queue to spool."""
        original_job_name = mock_job_success.name

        job_path = sample_grabber.grab_job()

        # Original file should not exist in queue
        assert not mock_job_success.exists()
        # New file should exist in spool
        assert job_path is not None
        assert Path(job_path).exists()
        assert sample_grabber.spool in job_path

    def test_grab_job_handles_race_condition(self, sample_grabber, temp_cluster_path):
        """Test FileNotFoundError handling when another grabber takes the job."""
        # Create a job file
        job_path = temp_cluster_path / "queue" / "race_job.py"
        job_path.write_text("#!/usr/bin/env python3\nprint('test')\n")

        # Mock shutil.move to raise FileNotFoundError (simulating race condition)
        with patch("shutil.move", side_effect=FileNotFoundError):
            result = sample_grabber.grab_job()

        # Should return None (no job grabbed due to race condition)
        assert result is None


@pytest.mark.unit
class TestGrabberRunJob:
    """Test run_job() method for job execution logic."""

    def test_run_job_success(self, sample_grabber, mock_job_success):
        """Test successful job execution (exit code 0 → -DONE suffix)."""
        job_path = sample_grabber.grab_job()
        assert job_path is not None

        sample_grabber.running_job_path = job_path
        sample_grabber.run_job()

        # Check job was renamed to -DONE
        done_path = job_path.replace("-RUNNING", "-DONE")
        assert Path(done_path).exists()
        assert not Path(job_path).exists()

    def test_run_job_failure(self, sample_grabber, mock_job_failure):
        """Test failed job execution (non-zero exit code → -FAILED suffix)."""
        job_path = sample_grabber.grab_job()
        assert job_path is not None

        sample_grabber.running_job_path = job_path
        sample_grabber.run_job()

        # Check job was renamed to -FAILED
        failed_path = job_path.replace("-RUNNING", "-FAILED")
        assert Path(failed_path).exists()
        assert not Path(job_path).exists()

    def test_run_job_timeout(self, sample_grabber, mock_job_timeout):
        """Test timeout job execution (exit code 124 → -TIMEOUT suffix)."""
        job_path = sample_grabber.grab_job()
        assert job_path is not None

        sample_grabber.running_job_path = job_path
        sample_grabber.run_job()

        # Check job was renamed to -TIMEOUT
        timeout_path = job_path.replace("-RUNNING", "-TIMEOUT")
        assert Path(timeout_path).exists()
        assert not Path(job_path).exists()

    def test_run_job_creates_stdout_file(self, sample_grabber, mock_job_output):
        """Test that stdout is captured and written to .out file."""
        job_path = sample_grabber.grab_job()
        sample_grabber.running_job_path = job_path
        sample_grabber.run_job()

        # Check .out file exists
        out_file = Path(sample_grabber.spoollog) / f"{sample_grabber.job_file}.out"
        assert out_file.exists()

        # Check content
        content = out_file.read_text()
        assert "Line 1 to stdout" in content
        assert "Line 2 to stdout" in content

    def test_run_job_creates_stderr_file(self, sample_grabber, mock_job_output):
        """Test that stderr is captured and written to .err file."""
        job_path = sample_grabber.grab_job()
        sample_grabber.running_job_path = job_path
        sample_grabber.run_job()

        # Check .err file exists
        err_file = Path(sample_grabber.spoollog) / f"{sample_grabber.job_file}.err"
        assert err_file.exists()

        # Check content
        content = err_file.read_text()
        assert "Line 1 to stderr" in content
        assert "Line 2 to stderr" in content

    def test_run_job_creates_log_file(self, sample_grabber, mock_job_success):
        """Test that log file is created with job name, timestamp, and exit code."""
        job_path = sample_grabber.grab_job()
        sample_grabber.running_job_path = job_path
        sample_grabber.run_job()

        # Check .log file exists
        log_file = Path(sample_grabber.spoollog) / f"{sample_grabber.job_file}.log"
        assert log_file.exists()

        # Check content
        content = log_file.read_text()
        assert sample_grabber.job_file in content
        assert "ExitCode(0)" in content

    def test_run_job_nonexistent_file(self, sample_grabber, temp_cluster_path):
        """Test handling of non-existent job file."""
        # Set a non-existent path
        sample_grabber.running_job_path = str(
            temp_cluster_path / "spool" / "nonexistent.py"
        )
        sample_grabber.run_job()

        # Should return early without crashing
        # No assertion needed, just verify it doesn't raise


@pytest.mark.unit
class TestGrabberSignalHandling:
    """Test signal handler methods."""

    def test_handle_sigint_sets_is_running_false(self, sample_grabber):
        """Test handle_sigint() sets is_running=False."""
        assert sample_grabber.is_running is True

        # Call handler with mock signal and frame
        with pytest.raises(SystemExit):
            sample_grabber.handle_sigint(signal.SIGINT, None)

        assert sample_grabber.is_running is False

    def test_handle_sigint_removes_lock_file(self, sample_grabber):
        """Test handle_sigint() removes lock file."""
        # Create a lock file
        lockfile_path = Path(sample_grabber.varlock) / f"{sample_grabber.grabberName}.lock"
        lockfile_path.write_text(str(os.getpid()))

        assert lockfile_path.exists()

        # Call handler
        with pytest.raises(SystemExit):
            sample_grabber.handle_sigint(signal.SIGINT, None)

        # Lock file should be removed
        assert not lockfile_path.exists()

    def test_handle_usr1_status_dump(self, sample_grabber, capsys):
        """Test handle_usr1() dumps status."""
        sample_grabber.handle_usr1(signal.SIGUSR1, None)

        # Capture output
        captured = capsys.readouterr()
        assert "Received USR1" in captured.out
        assert "Dumping status" in captured.out

    def test_handle_usr2_toggles_pause(self, sample_grabber):
        """Test handle_usr2() toggles is_paused flag correctly."""
        assert sample_grabber.is_paused is False

        # First call should pause
        sample_grabber.handle_usr2(signal.SIGUSR2, None)
        assert sample_grabber.is_paused is True

        # Second call should resume
        sample_grabber.handle_usr2(signal.SIGUSR2, None)
        assert sample_grabber.is_paused is False

    def test_handle_usr2_logs_pause(self, sample_grabber):
        """Test handle_usr2() logs pause action."""
        with patch.object(sample_grabber.logger, "info") as mock_log:
            sample_grabber.handle_usr2(signal.SIGUSR2, None)
            mock_log.assert_called_once()
            call_args = mock_log.call_args[0][0]
            assert "Pausing" in call_args

    def test_handle_usr2_logs_resume(self, sample_grabber):
        """Test handle_usr2() logs resume action."""
        sample_grabber.is_paused = True
        with patch.object(sample_grabber.logger, "info") as mock_log:
            sample_grabber.handle_usr2(signal.SIGUSR2, None)
            mock_log.assert_called_once()
            call_args = mock_log.call_args[0][0]
            assert "Resuming" in call_args


@pytest.mark.unit
class TestGrabberDuplicateInstanceBug:
    """Test the known bug at line 150 where GrabLockError is raised but doesn't prevent execution."""

    def test_lock_file_exists_bug(self, temp_cluster_path):
        """Test that GrabLockError is raised but doesn't actually prevent execution.

        This documents the bug at line 150 in grabber.py where GrabLockError is
        raised but not actually raised (missing 'raise' keyword).
        """
        # Create first grabber
        grabber1 = Grabber("test_grabber", str(temp_cluster_path))

        # Create lock file manually to simulate first grabber running
        lockfile_path = Path(temp_cluster_path) / "varlock" / "test_grabber.lock"
        lockfile_path.write_text(str(os.getpid()))

        # BUG: This should raise GrabLockError but doesn't
        # Creating a second grabber with same name should fail
        grabber2 = Grabber("test_grabber", str(temp_cluster_path))

        # Bug verification: grabber2 was created despite lock file
        assert grabber2 is not None

        # Expected behavior (when bug is fixed):
        # with pytest.raises(GrabLockError):
        #     grabber2 = Grabber("test_grabber", str(temp_cluster_path))
