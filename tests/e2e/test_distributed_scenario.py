"""End-to-end tests for distributed ScriptGrabber scenarios."""

import os
import time
import threading
from pathlib import Path
import pytest

from script_grabber.grabber import Grabber
from tests.fixtures import sample_jobs


@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.timeout(120)
class TestDistributedWorkflow:
    """Test complete distributed workflow with multiple grabbers."""

    def test_three_grabbers_mixed_jobs(self, temp_cluster_path):
        """Test 3 grabbers processing mix of success, failure, and timeout jobs."""
        # Create grabbers
        grabber1 = Grabber("grabber1", str(temp_cluster_path), job_timeout=60)
        grabber2 = Grabber("grabber2", str(temp_cluster_path), job_timeout=60)
        grabber3 = Grabber("grabber3", str(temp_cluster_path), job_timeout=60)

        # Create mixed job types
        jobs_created = []

        # Success jobs
        for i in range(3):
            job_path = temp_cluster_path / "queue" / f"success_{i}.py"
            job_path.write_text(sample_jobs.SUCCESS_JOB)
            jobs_created.append(job_path)

        # Failure jobs
        for i in range(2):
            job_path = temp_cluster_path / "queue" / f"failure_{i}.py"
            job_path.write_text(sample_jobs.FAILURE_JOB)
            jobs_created.append(job_path)

        # Timeout jobs
        for i in range(2):
            job_path = temp_cluster_path / "queue" / f"timeout_{i}.py"
            job_path.write_text(sample_jobs.TIMEOUT_JOB)
            jobs_created.append(job_path)

        # Process all jobs with all grabbers
        grabbers = [grabber1, grabber2, grabber3]
        processed_jobs = []

        while len(processed_jobs) < len(jobs_created):
            for grabber in grabbers:
                job = grabber.grab_job()
                if job:
                    grabber.running_job_path = job
                    grabber.run_job()
                    processed_jobs.append(job)

        # Verify all jobs processed
        assert len(processed_jobs) == len(jobs_created)

        # Check final states across all spools
        total_done = 0
        total_failed = 0
        total_timeout = 0

        for grabber in grabbers:
            spool = Path(grabber.spool)
            total_done += len(list(spool.glob("*-DONE")))
            total_failed += len(list(spool.glob("*-FAILED")))
            total_timeout += len(list(spool.glob("*-TIMEOUT")))

        assert total_done == 3
        assert total_failed == 2
        assert total_timeout == 2

    def test_control_and_common_queue_distribution(self, temp_cluster_path):
        """Test distribution of control queue and common queue jobs."""
        grabber1 = Grabber("grabber1", str(temp_cluster_path))
        grabber2 = Grabber("grabber2", str(temp_cluster_path))

        # Create control queue jobs for each grabber
        ctrl1 = Path(grabber1.ctrlqueue) / "ctrl1.py"
        ctrl1.write_text(sample_jobs.SUCCESS_JOB)

        ctrl2 = Path(grabber2.ctrlqueue) / "ctrl2.py"
        ctrl2.write_text(sample_jobs.SUCCESS_JOB)

        # Create common queue jobs
        for i in range(4):
            job_path = temp_cluster_path / "queue" / f"common_{i}.py"
            job_path.write_text(sample_jobs.SUCCESS_JOB)

        # Process all jobs
        all_processed = []

        for _ in range(10):  # Max iterations to prevent infinite loop
            for grabber in [grabber1, grabber2]:
                job = grabber.grab_job()
                if job:
                    grabber.running_job_path = job
                    grabber.run_job()
                    all_processed.append((grabber.grabberName, job))

        # Should have processed 6 total jobs
        assert len(all_processed) == 6

        # Each grabber should have processed its control queue job
        grabber1_jobs = [j for name, j in all_processed if name == "grabber1"]
        grabber2_jobs = [j for name, j in all_processed if name == "grabber2"]

        assert any("ctrl1" in j for j in grabber1_jobs)
        assert any("ctrl2" in j for j in grabber2_jobs)


@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.timeout(120)
class TestRealisticClusterSimulation:
    """Test realistic cluster environment simulation."""

    def test_realistic_job_mix_with_logging(self, temp_cluster_path):
        """Test realistic scenario with comprehensive logging."""
        # Create 3 grabbers
        grabbers = [
            Grabber(f"grabber{i}", str(temp_cluster_path), job_timeout=60)
            for i in range(1, 4)
        ]

        # Create diverse job set
        job_types = {
            "success": (sample_jobs.SUCCESS_JOB, 5),
            "failure": (sample_jobs.FAILURE_JOB, 3),
            "output": (sample_jobs.OUTPUT_JOB, 2),
            "timeout": (sample_jobs.TIMEOUT_JOB, 2),
        }

        total_jobs = 0
        for job_type, (script, count) in job_types.items():
            for i in range(count):
                job_path = temp_cluster_path / "queue" / f"{job_type}_{i}.py"
                job_path.write_text(script)
                total_jobs += 1

        # Process all jobs
        processed = 0
        max_iterations = total_jobs * 2  # Safety limit

        for iteration in range(max_iterations):
            if processed >= total_jobs:
                break

            for grabber in grabbers:
                job = grabber.grab_job()
                if job:
                    grabber.running_job_path = job
                    grabber.run_job()
                    processed += 1

        # Verify all jobs processed
        assert processed == total_jobs

        # Verify log files
        log_dir = Path(grabbers[0].spoollog)
        log_files = list(log_dir.glob("*.log"))
        out_files = list(log_dir.glob("*.out"))
        err_files = list(log_dir.glob("*.err"))

        assert len(log_files) == total_jobs
        assert len(out_files) == total_jobs
        assert len(err_files) == total_jobs

        # Verify expected outcomes
        all_done = []
        all_failed = []
        all_timeout = []

        for grabber in grabbers:
            spool = Path(grabber.spool)
            all_done.extend(list(spool.glob("*-DONE")))
            all_failed.extend(list(spool.glob("*-FAILED")))
            all_timeout.extend(list(spool.glob("*-TIMEOUT")))

        assert len(all_done) == 7  # success + output jobs
        assert len(all_failed) == 3
        assert len(all_timeout) == 2


@pytest.mark.e2e
@pytest.mark.slow
class TestJobExecutionVerification:
    """Test that jobs are executed exactly once and completely."""

    def test_no_duplicate_execution(self, temp_cluster_path):
        """Verify no job is executed twice by different grabbers."""
        grabbers = [
            Grabber(f"grabber{i}", str(temp_cluster_path))
            for i in range(1, 4)
        ]

        # Create jobs with unique identifiers
        num_jobs = 10
        for i in range(num_jobs):
            job_path = temp_cluster_path / "queue" / f"unique_job_{i}.py"
            job_path.write_text(sample_jobs.SUCCESS_JOB)

        # Track which jobs each grabber processes
        job_tracking = {grabber.grabberName: [] for grabber in grabbers}

        # Process all jobs
        total_processed = 0
        while total_processed < num_jobs:
            for grabber in grabbers:
                job = grabber.grab_job()
                if job:
                    job_name = Path(job).name
                    job_tracking[grabber.grabberName].append(job_name)
                    grabber.running_job_path = job
                    grabber.run_job()
                    total_processed += 1

        # Verify each job processed exactly once
        all_processed_jobs = []
        for jobs in job_tracking.values():
            all_processed_jobs.extend(jobs)

        assert len(all_processed_jobs) == num_jobs
        assert len(all_processed_jobs) == len(set(all_processed_jobs))  # All unique

    def test_all_jobs_reach_final_state(self, temp_cluster_path):
        """Verify all jobs reach a final state (DONE/FAILED/TIMEOUT)."""
        grabbers = [
            Grabber(f"grabber{i}", str(temp_cluster_path))
            for i in range(1, 3)
        ]

        # Create mixed jobs
        for i in range(5):
            job_path = temp_cluster_path / "queue" / f"job_{i}.py"
            job_path.write_text(sample_jobs.SUCCESS_JOB)

        # Process all
        processed = 0
        while processed < 5:
            for grabber in grabbers:
                job = grabber.grab_job()
                if job:
                    grabber.running_job_path = job
                    grabber.run_job()
                    processed += 1

        # Count final states
        final_state_count = 0
        for grabber in grabbers:
            spool = Path(grabber.spool)
            final_state_count += len(list(spool.glob("*-DONE")))
            final_state_count += len(list(spool.glob("*-FAILED")))
            final_state_count += len(list(spool.glob("*-TIMEOUT")))

            # Verify no jobs stuck in RUNNING state
            running = list(spool.glob("*-RUNNING"))
            assert len(running) == 0

        assert final_state_count == 5


@pytest.mark.e2e
@pytest.mark.slow
class TestGracefulShutdown:
    """Test graceful shutdown of multiple grabbers."""

    def test_cleanup_on_shutdown(self, temp_cluster_path):
        """Test that all grabbers clean up properly on shutdown."""
        grabbers = [
            Grabber(f"grabber{i}", str(temp_cluster_path))
            for i in range(1, 4)
        ]

        # Create lock files
        for grabber in grabbers:
            lock_path = Path(grabber.varlock) / f"{grabber.grabberName}.lock"
            lock_path.write_text(str(os.getpid()))

        # Simulate shutdown for each grabber
        for grabber in grabbers:
            lock_path = Path(grabber.varlock) / f"{grabber.grabberName}.lock"
            assert lock_path.exists()

            # Trigger shutdown
            with pytest.raises(SystemExit):
                grabber.handle_sigint(None, None)

            # Verify cleanup
            assert not lock_path.exists()


@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.timeout(120)
class TestCompleteExecutionHistory:
    """Test complete execution history validation."""

    def test_log_files_contain_complete_history(self, temp_cluster_path):
        """Validate log files contain complete execution history."""
        grabbers = [
            Grabber(f"grabber{i}", str(temp_cluster_path))
            for i in range(1, 3)
        ]

        # Create and process jobs
        num_jobs = 6
        for i in range(num_jobs):
            job_path = temp_cluster_path / "queue" / f"history_job_{i}.py"
            job_path.write_text(sample_jobs.SUCCESS_JOB)

        # Process all
        for _ in range(num_jobs):
            for grabber in grabbers:
                job = grabber.grab_job()
                if job:
                    grabber.running_job_path = job
                    grabber.run_job()

        # Verify log completeness
        log_dir = Path(grabbers[0].spoollog)
        log_files = list(log_dir.glob("history_job_*.log"))

        assert len(log_files) == num_jobs

        # Each log should contain required info
        for log_file in log_files:
            content = log_file.read_text()
            assert "ExitCode" in content
            # Should contain timestamp (14 digits)
            import re
            assert re.search(r"\d{14}", content)
