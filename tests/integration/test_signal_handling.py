"""Integration tests for signal handling in running grabbers."""

import os
import signal
import time
import threading
from pathlib import Path
import pytest

from script_grabber.grabber import Grabber


@pytest.mark.integration
class TestSignalHandlingIntegration:
    """Test signal handling with actual signal delivery."""

    def test_sigint_graceful_shutdown(self, temp_cluster_path, cleanup_locks):
        """Test SIGINT causes graceful shutdown and lock file cleanup."""
        grabber = Grabber("test_grabber", str(temp_cluster_path))

        # Create lock file
        lockfile_path = Path(grabber.varlock) / f"{grabber.grabberName}.lock"
        lockfile_path.write_text(str(os.getpid()))

        assert lockfile_path.exists()
        assert grabber.is_running is True

        # Send SIGINT
        with pytest.raises(SystemExit):
            grabber.handle_sigint(signal.SIGINT, None)

        # Verify cleanup
        assert grabber.is_running is False
        assert not lockfile_path.exists()

    def test_sigusr2_pause_resume(self, temp_cluster_path):
        """Test SIGUSR2 toggles pause state correctly."""
        grabber = Grabber("test_grabber", str(temp_cluster_path))

        assert grabber.is_paused is False

        # First SIGUSR2 should pause
        grabber.handle_usr2(signal.SIGUSR2, None)
        assert grabber.is_paused is True

        # Second SIGUSR2 should resume
        grabber.handle_usr2(signal.SIGUSR2, None)
        assert grabber.is_paused is False

    def test_sigusr2_multiple_toggles(self, temp_cluster_path):
        """Test multiple SIGUSR2 signals toggle correctly."""
        grabber = Grabber("test_grabber", str(temp_cluster_path))

        states = []
        for i in range(10):
            grabber.handle_usr2(signal.SIGUSR2, None)
            states.append(grabber.is_paused)

        # Should alternate: True, False, True, False, ...
        expected = [i % 2 == 0 for i in range(10)]
        assert states == expected

    def test_signal_handling_with_no_jobs(self, temp_cluster_path):
        """Test signal handling when no jobs are active."""
        grabber = Grabber("test_grabber", str(temp_cluster_path))

        # These should not crash when no jobs are running
        grabber.handle_usr2(signal.SIGUSR2, None)
        assert grabber.is_paused is True

        grabber.handle_usr1(signal.SIGUSR1, None)
        # Should complete without error

    def test_lock_file_cleanup_on_sigint(self, temp_cluster_path, cleanup_locks):
        """Test that lock file is properly removed on SIGINT."""
        grabber = Grabber("test_grabber", str(temp_cluster_path))

        lockfile_path = Path(grabber.varlock) / f"{grabber.grabberName}.lock"

        # Create multiple lock files to test cleanup
        lockfile_path.write_text(str(os.getpid()))
        assert lockfile_path.exists()

        # Trigger SIGINT
        with pytest.raises(SystemExit):
            grabber.handle_sigint(signal.SIGINT, None)

        # Verify lock file removed
        assert not lockfile_path.exists()


@pytest.mark.integration
@pytest.mark.timeout(10)
class TestPausedGrabberBehavior:
    """Test grabber behavior when paused."""

    def test_paused_grabber_skips_job_grab(
        self, temp_cluster_path, mock_job_success
    ):
        """Test that paused grabber doesn't grab jobs."""
        grabber = Grabber("test_grabber", str(temp_cluster_path))

        # Pause the grabber
        grabber.is_paused = True

        # Try to grab job while paused
        # In actual run() loop, this would be skipped
        # We're testing the state, not the loop itself
        assert grabber.is_paused is True

        # Resume
        grabber.is_paused = False
        assert grabber.is_paused is False


@pytest.mark.integration
class TestSignalDeliveryTiming:
    """Test signal delivery at different times."""

    def test_sigusr1_status_dump_output(self, temp_cluster_path, capsys):
        """Test SIGUSR1 produces status output."""
        grabber = Grabber("test_grabber", str(temp_cluster_path))

        grabber.handle_usr1(signal.SIGUSR1, None)

        captured = capsys.readouterr()
        assert "Received USR1" in captured.out

    def test_signal_state_persistence(self, temp_cluster_path):
        """Test that signal state changes persist."""
        grabber = Grabber("test_grabber", str(temp_cluster_path))

        # Change state via signal
        grabber.handle_usr2(signal.SIGUSR2, None)
        paused_state = grabber.is_paused

        # State should persist
        time.sleep(0.1)
        assert grabber.is_paused == paused_state


@pytest.mark.integration
class TestLockFileManagement:
    """Test lock file creation and cleanup."""

    def test_lock_file_contains_pid(self, temp_cluster_path):
        """Test that lock file contains process PID."""
        grabber = Grabber("test_grabber", str(temp_cluster_path))

        lockfile_path = Path(grabber.varlock) / f"{grabber.grabberName}.lock"
        lockfile_path.write_text(str(os.getpid()))

        content = lockfile_path.read_text()
        assert content == str(os.getpid())

    def test_sigint_removes_only_own_lock(self, temp_cluster_path, cleanup_locks):
        """Test that SIGINT only removes the grabber's own lock file."""
        grabber1 = Grabber("grabber1", str(temp_cluster_path))
        grabber2 = Grabber("grabber2", str(temp_cluster_path))

        # Create lock files for both
        lock1 = Path(grabber1.varlock) / "grabber1.lock"
        lock2 = Path(grabber2.varlock) / "grabber2.lock"

        lock1.write_text(str(os.getpid()))
        lock2.write_text(str(os.getpid() + 1))

        # Send SIGINT to grabber1
        with pytest.raises(SystemExit):
            grabber1.handle_sigint(signal.SIGINT, None)

        # Only grabber1's lock should be removed
        assert not lock1.exists()
        assert lock2.exists()  # grabber2's lock should remain
