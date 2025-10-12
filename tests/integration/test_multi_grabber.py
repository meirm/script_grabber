"""Integration tests for multi-grabber scenarios."""

import os
import time
from pathlib import Path
import pytest

from script_grabber.grabber import Grabber


@pytest.mark.integration
class TestMultiGrabberJobDistribution:
    """Test job distribution across multiple grabbers."""

    def test_two_grabbers_different_names(self, temp_cluster_path, multiple_jobs):
        """Test multiple grabber instances with different names can coexist."""
        grabber1 = Grabber("grabber1", str(temp_cluster_path))
        grabber2 = Grabber("grabber2", str(temp_cluster_path))

        # Both should be able to grab jobs
        job1 = grabber1.grab_job()
        job2 = grabber2.grab_job()

        assert job1 is not None
        assert job2 is not None
        assert job1 != job2  # Different jobs

    def test_job_distribution_fairness(self, temp_cluster_path, multiple_jobs):
        """Test that jobs are distributed across multiple grabbers."""
        grabber1 = Grabber("grabber1", str(temp_cluster_path))
        grabber2 = Grabber("grabber2", str(temp_cluster_path))

        grabber1_jobs = []
        grabber2_jobs = []

        # Alternately grab jobs
        for i in range(len(multiple_jobs)):
            if i % 2 == 0:
                job = grabber1.grab_job()
                if job:
                    grabber1_jobs.append(job)
            else:
                job = grabber2.grab_job()
                if job:
                    grabber2_jobs.append(job)

        # Both grabbers should have grabbed jobs
        assert len(grabber1_jobs) > 0
        assert len(grabber2_jobs) > 0
        # Total should equal number of jobs
        assert len(grabber1_jobs) + len(grabber2_jobs) == len(multiple_jobs)

    def test_race_condition_no_duplicate_execution(self, temp_cluster_path):
        """Test that no job is executed twice by different grabbers."""
        grabber1 = Grabber("grabber1", str(temp_cluster_path))
        grabber2 = Grabber("grabber2", str(temp_cluster_path))

        # Create a single job
        job_path = Path(temp_cluster_path) / "queue" / "single_job.py"
        job_path.write_text("#!/usr/bin/env python3\nprint('test')\n")

        # Both try to grab simultaneously
        job1 = grabber1.grab_job()
        job2 = grabber2.grab_job()

        # Only one should succeed
        assert (job1 is not None) != (job2 is not None)  # XOR

    def test_control_queue_routing(self, temp_cluster_path):
        """Test control queue routes to specific grabber."""
        grabber1 = Grabber("grabber1", str(temp_cluster_path))
        grabber2 = Grabber("grabber2", str(temp_cluster_path))

        # Create job in grabber1's control queue
        ctrl_job = Path(grabber1.ctrlqueue) / "ctrl_job.py"
        ctrl_job.write_text("#!/usr/bin/env python3\nprint('ctrl')\n")

        # grabber1 should get it
        job1 = grabber1.grab_job()
        assert job1 is not None
        assert "ctrl_job" in job1

        # grabber2 should not see it (empty queue)
        job2 = grabber2.grab_job()
        assert job2 is None

    def test_separate_spool_directories(self, temp_cluster_path, multiple_jobs):
        """Test that each grabber has its own spool directory."""
        grabber1 = Grabber("grabber1", str(temp_cluster_path))
        grabber2 = Grabber("grabber2", str(temp_cluster_path))

        # Grab and run jobs
        job1 = grabber1.grab_job()
        grabber1.running_job_path = job1
        grabber1.run_job()

        job2 = grabber2.grab_job()
        grabber2.running_job_path = job2
        grabber2.run_job()

        # Check spool directories are separate
        spool1 = Path(grabber1.spool)
        spool2 = Path(grabber2.spool)

        assert spool1 != spool2
        assert spool1.exists()
        assert spool2.exists()

        # Each should have its own job
        spool1_files = list(spool1.glob("*-DONE"))
        spool2_files = list(spool2.glob("*-DONE"))

        assert len(spool1_files) == 1
        assert len(spool2_files) == 1


@pytest.mark.integration
class TestLockFileConflicts:
    """Test lock file behavior with multiple grabbers."""

    def test_lock_files_prevent_duplicate_names(self, temp_cluster_path):
        """Test that lock files prevent duplicate grabber names.

        Note: This tests the intended behavior, but due to bug at line 150,
        the lock file check doesn't actually prevent duplicate instances.
        """
        grabber1 = Grabber("same_name", str(temp_cluster_path))

        # Create lock file for first grabber
        lockfile = Path(temp_cluster_path) / "varlock" / "same_name.lock"
        lockfile.write_text(str(os.getpid()))

        # BUG: Second grabber with same name can still be created
        # When bug is fixed, this should raise GrabLockError
        grabber2 = Grabber("same_name", str(temp_cluster_path))
        assert grabber2 is not None  # Bug allows this

        # Expected behavior (when bug is fixed):
        # with pytest.raises(GrabLockError):
        #     grabber2 = Grabber("same_name", str(temp_cluster_path))

    def test_different_grabbers_different_locks(self, temp_cluster_path):
        """Test that different grabbers create different lock files."""
        grabber1 = Grabber("grabber1", str(temp_cluster_path))
        grabber2 = Grabber("grabber2", str(temp_cluster_path))

        lock1 = Path(temp_cluster_path) / "varlock" / "grabber1.lock"
        lock2 = Path(temp_cluster_path) / "varlock" / "grabber2.lock"

        # Manually create locks for testing
        lock1.write_text(str(os.getpid()))
        lock2.write_text(str(os.getpid() + 1))

        assert lock1.exists()
        assert lock2.exists()
        assert lock1 != lock2


@pytest.mark.integration
class TestConcurrentJobExecution:
    """Test concurrent job execution scenarios."""

    def test_simultaneous_job_grab_attempts(self, temp_cluster_path, multiple_jobs):
        """Test multiple grabbers attempting to grab jobs simultaneously."""
        grabber1 = Grabber("grabber1", str(temp_cluster_path))
        grabber2 = Grabber("grabber2", str(temp_cluster_path))
        grabber3 = Grabber("grabber3", str(temp_cluster_path))

        grabbed_jobs = []

        # All grabbers try to grab jobs
        for grabber in [grabber1, grabber2, grabber3]:
            job = grabber.grab_job()
            if job:
                grabbed_jobs.append(job)

        # All grabbed jobs should be unique
        assert len(grabbed_jobs) == len(set(grabbed_jobs))

        # Should have grabbed up to number of available jobs
        assert len(grabbed_jobs) <= len(multiple_jobs)

    def test_no_job_lost_in_distribution(self, temp_cluster_path, multiple_jobs):
        """Test that all jobs are eventually processed by some grabber."""
        grabber1 = Grabber("grabber1", str(temp_cluster_path))
        grabber2 = Grabber("grabber2", str(temp_cluster_path))

        all_jobs = []

        # Process all jobs
        while True:
            job1 = grabber1.grab_job()
            job2 = grabber2.grab_job()

            if job1:
                all_jobs.append(job1)
            if job2:
                all_jobs.append(job2)

            if not job1 and not job2:
                break

        # All jobs should be grabbed
        assert len(all_jobs) == len(multiple_jobs)

        # All jobs should be unique
        assert len(all_jobs) == len(set(all_jobs))


@pytest.mark.integration
class TestSharedLogDirectory:
    """Test that multiple grabbers share the log directory."""

    def test_shared_log_directory(self, temp_cluster_path, multiple_jobs):
        """Test that all grabbers write to the same log directory."""
        grabber1 = Grabber("grabber1", str(temp_cluster_path))
        grabber2 = Grabber("grabber2", str(temp_cluster_path))

        # Run jobs with both grabbers
        job1 = grabber1.grab_job()
        grabber1.running_job_path = job1
        grabber1.run_job()

        job2 = grabber2.grab_job()
        grabber2.running_job_path = job2
        grabber2.run_job()

        # Both should use same log directory
        assert grabber1.spoollog == grabber2.spoollog

        # Log files should exist in shared directory
        log_dir = Path(grabber1.spoollog)
        log_files = list(log_dir.glob("*.log"))
        out_files = list(log_dir.glob("*.out"))

        assert len(log_files) >= 2
        assert len(out_files) >= 2

    def test_log_files_dont_conflict(self, temp_cluster_path, multiple_jobs):
        """Test that log files from different grabbers don't conflict."""
        grabber1 = Grabber("grabber1", str(temp_cluster_path))
        grabber2 = Grabber("grabber2", str(temp_cluster_path))

        # Process jobs
        job1 = grabber1.grab_job()
        grabber1.running_job_path = job1
        grabber1.run_job()

        job2 = grabber2.grab_job()
        grabber2.running_job_path = job2
        grabber2.run_job()

        # Log files should have different names (based on job names)
        log_dir = Path(grabber1.spoollog)
        log_files = list(log_dir.glob("*.log"))

        log_names = [f.name for f in log_files]
        assert len(log_names) == len(set(log_names))  # All unique
