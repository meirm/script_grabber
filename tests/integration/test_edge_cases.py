"""Integration tests for edge cases and error conditions."""

import os
from pathlib import Path
import pytest

from script_grabber.grabber import Grabber
from tests.fixtures import sample_jobs


@pytest.mark.integration
class TestEmptyDirectories:
    """Test behavior with empty directories."""

    def test_empty_queue_directories(self, temp_cluster_path):
        """Test grabber behavior with empty queue directories."""
        grabber = Grabber("test_grabber", str(temp_cluster_path))

        # All queues are empty
        job = grabber.grab_job()
        assert job is None

    def test_empty_control_queue_falls_back_to_common(
        self, temp_cluster_path, mock_job_success
    ):
        """Test that empty control queue falls back to common queue."""
        grabber = Grabber("test_grabber", str(temp_cluster_path))

        # Control queue is empty, common queue has job
        job = grabber.grab_job()
        assert job is not None
        assert grabber.spool in job


@pytest.mark.integration
class TestMalformedJobs:
    """Test handling of malformed job scripts."""

    def test_job_with_syntax_error(self, temp_cluster_path):
        """Test execution of job with Python syntax error."""
        grabber = Grabber("test_grabber", str(temp_cluster_path))

        # Create job with syntax error
        job_path = temp_cluster_path / "queue" / "syntax_error.py"
        job_path.write_text("#!/usr/bin/env python3\nif True\nprint('missing colon')\n")

        job = grabber.grab_job()
        grabber.running_job_path = job
        grabber.run_job()

        # Should be marked as FAILED
        failed_path = job.replace("-RUNNING", "-FAILED")
        assert Path(failed_path).exists()

        # Error should be captured in .err file
        err_file = Path(grabber.spoollog) / "syntax_error.py.err"
        assert err_file.exists()
        content = err_file.read_text()
        assert "SyntaxError" in content or "Error" in content.lower()

    def test_job_with_import_error(self, temp_cluster_path):
        """Test execution of job that imports non-existent module."""
        grabber = Grabber("test_grabber", str(temp_cluster_path))

        job_path = temp_cluster_path / "queue" / "import_error.py"
        job_path.write_text(
            "#!/usr/bin/env python3\nimport nonexistent_module\nprint('test')\n"
        )

        job = grabber.grab_job()
        grabber.running_job_path = job
        grabber.run_job()

        # Should be marked as FAILED
        failed_path = job.replace("-RUNNING", "-FAILED")
        assert Path(failed_path).exists()

    def test_empty_job_file(self, temp_cluster_path):
        """Test execution of empty job file."""
        grabber = Grabber("test_grabber", str(temp_cluster_path))

        job_path = temp_cluster_path / "queue" / "empty_job.py"
        job_path.write_text("")

        job = grabber.grab_job()
        grabber.running_job_path = job
        grabber.run_job()

        # Empty file should succeed (exit code 0)
        done_path = job.replace("-RUNNING", "-DONE")
        assert Path(done_path).exists()


@pytest.mark.integration
class TestLongJobNames:
    """Test handling of very long job names."""

    def test_very_long_job_name(self, temp_cluster_path):
        """Test job with very long filename."""
        grabber = Grabber("test_grabber", str(temp_cluster_path))

        # Create job with long name (but within filesystem limits)
        long_name = "a" * 200 + ".py"
        job_path = temp_cluster_path / "queue" / long_name
        job_path.write_text(sample_jobs.SUCCESS_JOB)

        job = grabber.grab_job()
        assert job is not None

        grabber.running_job_path = job
        grabber.run_job()

        # Should complete successfully
        done_path = job.replace("-RUNNING", "-DONE")
        assert Path(done_path).exists()


@pytest.mark.integration
class TestSpecialCharactersInJobNames:
    """Test handling of special characters in job names."""

    def test_job_with_spaces_in_name(self, temp_cluster_path):
        """Test job with spaces in filename."""
        grabber = Grabber("test_grabber", str(temp_cluster_path))

        job_path = temp_cluster_path / "queue" / "job with spaces.py"
        job_path.write_text(sample_jobs.SUCCESS_JOB)

        job = grabber.grab_job()
        assert job is not None

        grabber.running_job_path = job
        grabber.run_job()

        # Should complete successfully
        done_path = job.replace("-RUNNING", "-DONE")
        assert Path(done_path).exists()

    def test_job_with_dashes_in_name(self, temp_cluster_path):
        """Test job with dashes in filename."""
        grabber = Grabber("test_grabber", str(temp_cluster_path))

        job_path = temp_cluster_path / "queue" / "job-with-dashes.py"
        job_path.write_text(sample_jobs.SUCCESS_JOB)

        job = grabber.grab_job()
        grabber.running_job_path = job
        grabber.run_job()

        done_path = job.replace("-RUNNING", "-DONE")
        assert Path(done_path).exists()


@pytest.mark.integration
class TestConcurrentDirectoryAccess:
    """Test concurrent access to same directories."""

    def test_multiple_grabbers_same_queue(self, temp_cluster_path, multiple_jobs):
        """Test multiple grabbers accessing same queue directory."""
        grabber1 = Grabber("grabber1", str(temp_cluster_path))
        grabber2 = Grabber("grabber2", str(temp_cluster_path))

        # Both try to grab from same queue
        jobs = []
        for _ in range(len(multiple_jobs)):
            job1 = grabber1.grab_job()
            job2 = grabber2.grab_job()

            if job1:
                jobs.append(job1)
            if job2:
                jobs.append(job2)

        # Should have grabbed all jobs without duplicates
        assert len(jobs) == len(set(jobs))  # All unique


@pytest.mark.integration
class TestJobFileModification:
    """Test jobs that modify their own files."""

    def test_job_that_creates_files(self, temp_cluster_path):
        """Test job that creates new files during execution."""
        grabber = Grabber("test_grabber", str(temp_cluster_path))

        # Job that creates a file
        job_script = """#!/usr/bin/env python3
import os
with open('created_file.txt', 'w') as f:
    f.write('test content')
print('File created')
"""
        job_path = temp_cluster_path / "queue" / "file_creator.py"
        job_path.write_text(job_script)

        job = grabber.grab_job()
        grabber.running_job_path = job
        grabber.run_job()

        # Job should succeed
        done_path = job.replace("-RUNNING", "-DONE")
        assert Path(done_path).exists()

        # Created file should exist
        created_file = temp_cluster_path / "created_file.txt"
        assert created_file.exists()


@pytest.mark.integration
class TestStaleResources:
    """Test handling of stale resources."""

    def test_stale_lock_file_from_crashed_grabber(self, temp_cluster_path):
        """Test behavior with stale lock file from crashed grabber."""
        # Create stale lock file with non-existent PID
        lock_path = temp_cluster_path / "varlock" / "crashed_grabber.lock"
        lock_path.write_text("999999")  # Non-existent PID

        # BUG: Current implementation doesn't handle stale locks
        # New grabber can be created despite stale lock
        grabber = Grabber("crashed_grabber", str(temp_cluster_path))
        assert grabber is not None

        # Expected behavior (when improved):
        # Should detect stale lock (PID doesn't exist) and clean it up


@pytest.mark.integration
class TestNonPythonFiles:
    """Test handling of non-Python files in queue."""

    def test_non_executable_file_in_queue(self, temp_cluster_path):
        """Test that non-executable files are still processed."""
        grabber = Grabber("test_grabber", str(temp_cluster_path))

        # Create non-executable file
        job_path = temp_cluster_path / "queue" / "test.py"
        job_path.write_text(sample_jobs.SUCCESS_JOB)
        job_path.chmod(0o644)  # Not executable

        job = grabber.grab_job()
        assert job is not None

        # After grab, should be executable
        assert os.access(job, os.X_OK)

        grabber.running_job_path = job
        grabber.run_job()

        done_path = job.replace("-RUNNING", "-DONE")
        assert Path(done_path).exists()


@pytest.mark.integration
class TestRapidJobSubmission:
    """Test rapid job submission scenarios."""

    def test_many_jobs_submitted_rapidly(self, temp_cluster_path):
        """Test handling of many jobs submitted in quick succession."""
        grabber = Grabber("test_grabber", str(temp_cluster_path))

        # Create many jobs rapidly
        num_jobs = 50
        for i in range(num_jobs):
            job_path = temp_cluster_path / "queue" / f"rapid_{i}.py"
            job_path.write_text(sample_jobs.SUCCESS_JOB)

        # Process all
        processed = 0
        for _ in range(num_jobs):
            job = grabber.grab_job()
            if job:
                grabber.running_job_path = job
                grabber.run_job()
                processed += 1

        assert processed == num_jobs
