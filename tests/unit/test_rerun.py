#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for the rerun functionality in the ScriptGrabber system.

These tests verify the rerun_task method behavior with mocked file operations
for fast, isolated testing.
"""

import os
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from script_grabber.grabber import Grabber
from script_grabber.grabexceptions import GrabTaskNotFoundError, GrabRerunError


@pytest.mark.unit
class TestRerunTask:
    """Unit tests for the rerun_task method."""

    def test_rerun_done_job_to_common_queue(self, temp_cluster_path):
        """Test successfully rerunning a DONE job to the common queue."""
        grabber = Grabber("test_grabber", temp_cluster_path)

        # Create a mock DONE job in the spool directory
        done_job = "test_job.py-20240101120000-DONE"
        done_job_path = os.path.join(grabber.spool, done_job)
        os.makedirs(grabber.spool, exist_ok=True)

        # Create the job file with actual content
        with open(done_job_path, "w") as f:
            f.write("#!/usr/bin/env python3\nprint('test')\n")

        # Rerun the job
        result = grabber.rerun_task("test_job.py", "common")

        # Verify the job was placed in the common queue
        assert result == os.path.join(grabber.queue, "test_job.py")
        assert os.path.exists(result)

        # Verify original job is still in spool
        assert os.path.exists(done_job_path)

    def test_rerun_failed_job_to_common_queue(self, temp_cluster_path):
        """Test successfully rerunning a FAILED job to the common queue."""
        grabber = Grabber("test_grabber", temp_cluster_path)

        # Create a mock FAILED job in the spool directory
        failed_job = "test_job.py-20240101120000-FAILED"
        failed_job_path = os.path.join(grabber.spool, failed_job)
        os.makedirs(grabber.spool, exist_ok=True)

        with open(failed_job_path, "w") as f:
            f.write("#!/usr/bin/env python3\nprint('test')\n")

        # Rerun the job
        result = grabber.rerun_task("test_job.py", "common")

        # Verify the job was placed in the common queue
        assert result == os.path.join(grabber.queue, "test_job.py")
        assert os.path.exists(result)

        # Verify original job is still in spool
        assert os.path.exists(failed_job_path)

    def test_rerun_timeout_job_to_control_queue(self, temp_cluster_path):
        """Test successfully rerunning a TIMEOUT job to the control queue."""
        grabber = Grabber("test_grabber", temp_cluster_path)

        # Create a mock TIMEOUT job in the spool directory
        timeout_job = "test_job.py-20240101120000-TIMEOUT"
        timeout_job_path = os.path.join(grabber.spool, timeout_job)
        os.makedirs(grabber.spool, exist_ok=True)

        with open(timeout_job_path, "w") as f:
            f.write("#!/usr/bin/env python3\nprint('test')\n")

        # Rerun the job to control queue
        result = grabber.rerun_task("test_job.py", "control")

        # Verify the job was placed in the control queue
        assert result == os.path.join(grabber.ctrlqueue, "test_job.py")
        assert os.path.exists(result)

        # Verify original job is still in spool
        assert os.path.exists(timeout_job_path)

    def test_rerun_nonexistent_job_raises_exception(self, temp_cluster_path):
        """Test that rerunning a nonexistent job raises GrabTaskNotFoundError."""
        grabber = Grabber("test_grabber", temp_cluster_path)

        # Attempt to rerun a job that doesn't exist
        with pytest.raises(GrabTaskNotFoundError) as exc_info:
            grabber.rerun_task("nonexistent_job.py", "common")

        assert "not found" in str(exc_info.value.message).lower()
        assert "nonexistent_job.py" in exc_info.value.message

    def test_rerun_creates_temp_directory(self, temp_cluster_path):
        """Test that rerun creates the temp directory if it doesn't exist."""
        grabber = Grabber("test_grabber", temp_cluster_path)

        # Create a mock DONE job
        done_job = "test_job.py-20240101120000-DONE"
        done_job_path = os.path.join(grabber.spool, done_job)
        os.makedirs(grabber.spool, exist_ok=True)

        with open(done_job_path, "w") as f:
            f.write("#!/usr/bin/env python3\nprint('test')\n")

        # Remove temp directory if it exists
        temp_dir = os.path.join(temp_cluster_path, "temp")
        if os.path.exists(temp_dir):
            os.rmdir(temp_dir)

        # Rerun the job
        grabber.rerun_task("test_job.py", "common")

        # Verify temp directory was created
        assert os.path.exists(temp_dir)
        assert os.path.isdir(temp_dir)

    def test_rerun_preserves_original_job(self, temp_cluster_path):
        """Test that rerun preserves the original job file in spool."""
        grabber = Grabber("test_grabber", temp_cluster_path)

        # Create a mock DONE job with specific content
        done_job = "test_job.py-20240101120000-DONE"
        done_job_path = os.path.join(grabber.spool, done_job)
        os.makedirs(grabber.spool, exist_ok=True)

        original_content = "#!/usr/bin/env python3\nprint('original')\n"
        with open(done_job_path, "w") as f:
            f.write(original_content)

        # Rerun the job
        grabber.rerun_task("test_job.py", "common")

        # Verify original job still exists with same content
        assert os.path.exists(done_job_path)
        with open(done_job_path, "r") as f:
            assert f.read() == original_content

    def test_rerun_generates_correct_job_name(self, temp_cluster_path):
        """Test that rerun generates correct job name without timestamp/status."""
        grabber = Grabber("test_grabber", temp_cluster_path)

        # Create a mock DONE job with timestamp and status
        done_job = "my_complex_job.py-20240101120000-DONE"
        done_job_path = os.path.join(grabber.spool, done_job)
        os.makedirs(grabber.spool, exist_ok=True)

        with open(done_job_path, "w") as f:
            f.write("#!/usr/bin/env python3\nprint('test')\n")

        # Rerun the job
        result = grabber.rerun_task("my_complex_job.py", "common")

        # Verify the generated job name is correct
        expected_path = os.path.join(grabber.queue, "my_complex_job.py")
        assert result == expected_path

        # Verify the file exists with correct name
        assert os.path.exists(expected_path)
        assert os.path.basename(expected_path) == "my_complex_job.py"

    def test_rerun_selects_most_recent_job(self, temp_cluster_path):
        """Test that rerun selects the most recent job when multiple exist."""
        grabber = Grabber("test_grabber", temp_cluster_path)
        os.makedirs(grabber.spool, exist_ok=True)

        # Create multiple versions of the same job
        older_job = "test_job.py-20240101120000-DONE"
        newer_job = "test_job.py-20240102120000-DONE"

        older_content = "#!/usr/bin/env python3\nprint('older')\n"
        newer_content = "#!/usr/bin/env python3\nprint('newer')\n"

        with open(os.path.join(grabber.spool, older_job), "w") as f:
            f.write(older_content)

        with open(os.path.join(grabber.spool, newer_job), "w") as f:
            f.write(newer_content)

        # Rerun the job
        result = grabber.rerun_task("test_job.py", "common")

        # Verify the newer version was used
        with open(result, "r") as f:
            content = f.read()
            assert content == newer_content

    def test_rerun_invalid_queue_type_raises_exception(self, temp_cluster_path):
        """Test that invalid queue type raises GrabRerunError."""
        grabber = Grabber("test_grabber", temp_cluster_path)

        # Create a mock DONE job
        done_job = "test_job.py-20240101120000-DONE"
        done_job_path = os.path.join(grabber.spool, done_job)
        os.makedirs(grabber.spool, exist_ok=True)

        with open(done_job_path, "w") as f:
            f.write("#!/usr/bin/env python3\nprint('test')\n")

        # Attempt to rerun with invalid queue type
        with pytest.raises(GrabRerunError) as exc_info:
            grabber.rerun_task("test_job.py", "invalid_queue")

        assert "invalid queue type" in str(exc_info.value.message).lower()

    def test_rerun_with_job_name_without_extension(self, temp_cluster_path):
        """Test rerunning with job name that doesn't have .py extension."""
        grabber = Grabber("test_grabber", temp_cluster_path)
        os.makedirs(grabber.spool, exist_ok=True)

        # Create a job without .py extension
        done_job = "test_script-20240101120000-DONE"
        done_job_path = os.path.join(grabber.spool, done_job)

        with open(done_job_path, "w") as f:
            f.write("#!/usr/bin/env python3\nprint('test')\n")

        # Rerun the job (should work with or without extension)
        result = grabber.rerun_task("test_script", "common")

        # Verify the job was requeued
        assert os.path.exists(result)
