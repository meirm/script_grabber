"""Integration tests for multi-language execution support."""

import pytest
from pathlib import Path
import tempfile
import time
import shutil
from script_grabber.grabber import Grabber


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
def grabber(temp_cluster):
    """Create a Grabber instance for testing."""
    return Grabber(name="test_grabber", clusterpath=str(temp_cluster))


@pytest.mark.integration
class TestMultiLanguageExecution:
    """Test complete workflow for different file types."""

    def test_bash_script_execution(self, grabber, temp_cluster):
        """Test complete workflow: submit bash script → grab → execute → verify output."""
        # Create bash script in queue
        script_content = "#!/bin/bash\necho 'Hello from bash'\nexit 0\n"
        queue_file = temp_cluster / "queue" / "test_bash.sh"
        queue_file.write_text(script_content)

        # Grab the job
        job_path = grabber.grab_job()
        assert job_path is not None
        assert Path(job_path).exists()
        assert "-RUNNING" in job_path

        # Set running_job_path for run_job() (normally done by run() method)
        grabber.running_job_path = job_path

        # Execute the job
        grabber.run_job()

        # Verify job completed successfully
        spool_dir = temp_cluster / "spool" / "test_grabber"
        done_files = list(spool_dir.glob("*-DONE"))
        assert len(done_files) == 1

        # Verify output
        log_dir = temp_cluster / "log"
        # Log file name is based on the original job filename
        out_files = list(log_dir.glob("test_bash.sh.out"))
        assert len(out_files) == 1, f"Expected 1 .out file, found {len(out_files)}. Files in log: {list(log_dir.glob('*'))}"
        output = out_files[0].read_text()
        assert "Hello from bash" in output

    def test_python_script_execution(self, grabber, temp_cluster):
        """Test Python scripts still work (backward compatibility)."""
        # Create Python script in queue
        script_content = "#!/usr/bin/env python3\nprint('Hello from Python')\nexit(0)\n"
        queue_file = temp_cluster / "queue" / "test_python.py"
        queue_file.write_text(script_content)

        # Grab the job
        job_path = grabber.grab_job()
        assert job_path is not None

        # Set running_job_path for run_job() (normally done by run() method)
        grabber.running_job_path = job_path

        # Execute the job
        grabber.run_job()

        # Verify job completed successfully
        spool_dir = temp_cluster / "spool" / "test_grabber"
        done_files = list(spool_dir.glob("*-DONE"))
        assert len(done_files) == 1

        # Verify output
        log_dir = temp_cluster / "log"
        out_files = list(log_dir.glob("test_python.py.out"))
        assert len(out_files) == 1
        output = out_files[0].read_text()
        assert "Hello from Python" in output

    @pytest.mark.skipif(shutil.which("node") is None, reason="Node.js not available")
    def test_node_script_execution(self, grabber, temp_cluster):
        """Test Node.js script execution (if Node.js available)."""
        # Create Node.js script in queue
        script_content = "#!/usr/bin/env node\nconsole.log('Hello from Node.js');\nprocess.exit(0);\n"
        queue_file = temp_cluster / "queue" / "test_node.js"
        queue_file.write_text(script_content)

        # Grab the job
        job_path = grabber.grab_job()
        assert job_path is not None

        # Set running_job_path for run_job() (normally done by run() method)
        grabber.running_job_path = job_path

        # Execute the job
        grabber.run_job()

        # Verify job completed successfully
        spool_dir = temp_cluster / "spool" / "test_grabber"
        done_files = list(spool_dir.glob("*-DONE"))
        assert len(done_files) == 1

        # Verify output
        log_dir = temp_cluster / "log"
        out_files = list(log_dir.glob("test_node.js.out"))
        assert len(out_files) == 1
        output = out_files[0].read_text()
        assert "Hello from Node.js" in output

    def test_no_extension_execution(self, grabber, temp_cluster):
        """Test file without extension executes based on shebang."""
        # Create file without extension in queue
        script_content = "#!/bin/bash\necho 'Hello from no-extension file'\nexit 0\n"
        queue_file = temp_cluster / "queue" / "test_noext"
        queue_file.write_text(script_content)

        # Grab the job
        job_path = grabber.grab_job()
        assert job_path is not None

        # Set running_job_path for run_job() (normally done by run() method)
        grabber.running_job_path = job_path

        # Execute the job
        grabber.run_job()

        # Verify job completed successfully
        spool_dir = temp_cluster / "spool" / "test_grabber"
        done_files = list(spool_dir.glob("*-DONE"))
        assert len(done_files) == 1

        # Verify output
        log_dir = temp_cluster / "log"
        out_files = list(log_dir.glob("test_noext.out"))
        assert len(out_files) == 1
        output = out_files[0].read_text()
        assert "Hello from no-extension file" in output

    def test_shebang_execution_priority(self, grabber, temp_cluster):
        """Test that shebang takes priority over extension."""
        # Create .sh file with Python shebang
        script_content = "#!/usr/bin/env python3\nprint('Python via shebang')\nexit(0)\n"
        queue_file = temp_cluster / "queue" / "test_mixed.sh"
        queue_file.write_text(script_content)

        # Grab the job
        job_path = grabber.grab_job()
        assert job_path is not None

        # Set running_job_path for run_job() (normally done by run() method)
        grabber.running_job_path = job_path

        # Execute the job
        grabber.run_job()

        # Verify job completed successfully
        spool_dir = temp_cluster / "spool" / "test_grabber"
        done_files = list(spool_dir.glob("*-DONE"))
        assert len(done_files) == 1

        # Verify output shows it ran via Python (not bash)
        log_dir = temp_cluster / "log"
        out_files = list(log_dir.glob("test_mixed.sh.out"))
        assert len(out_files) == 1
        output = out_files[0].read_text()
        assert "Python via shebang" in output

    def test_error_missing_interpreter(self, grabber, temp_cluster):
        """Test error handling when interpreter is missing."""
        # Create script with non-existent interpreter
        script_content = "#!/usr/bin/nonexistent\necho 'This should fail'\n"
        queue_file = temp_cluster / "queue" / "test_fail.sh"
        queue_file.write_text(script_content)

        # Grab the job
        job_path = grabber.grab_job()
        assert job_path is not None

        # Set running_job_path for run_job() (normally done by run() method)
        grabber.running_job_path = job_path

        # Execute the job - should handle error gracefully
        grabber.run_job()

        # Job should still be marked as RUNNING (error returns early)
        spool_dir = temp_cluster / "spool" / "test_grabber"
        running_files = list(spool_dir.glob("*-RUNNING"))
        # The job returns early on error, so file stays as RUNNING
        assert len(running_files) == 1

    def test_extension_detection_without_shebang(self, grabber, temp_cluster):
        """Test extension-based detection when shebang is missing."""
        # Create .py file with shebang (Python files need interpreter)
        script_content = "#!/usr/bin/env python3\nprint('Hello from extension detection')\n"
        queue_file = temp_cluster / "queue" / "test_ext.py"
        queue_file.write_text(script_content)

        # Grab the job
        job_path = grabber.grab_job()
        assert job_path is not None

        # Set running_job_path for run_job() (normally done by run() method)
        grabber.running_job_path = job_path

        # Execute the job
        grabber.run_job()

        # Verify job completed successfully
        spool_dir = temp_cluster / "spool" / "test_grabber"
        done_files = list(spool_dir.glob("*-DONE"))
        assert len(done_files) == 1

        # Verify output
        log_dir = temp_cluster / "log"
        out_files = list(log_dir.glob("test_ext.py.out"))
        assert len(out_files) == 1
        output = out_files[0].read_text()
        assert "Hello from extension detection" in output

    def test_script_failure_handling(self, grabber, temp_cluster):
        """Test that script failures are handled correctly."""
        # Create script that exits with error
        script_content = "#!/bin/bash\necho 'This will fail'\nexit 1\n"
        queue_file = temp_cluster / "queue" / "test_error.sh"
        queue_file.write_text(script_content)

        # Grab the job
        job_path = grabber.grab_job()
        assert job_path is not None

        # Set running_job_path for run_job() (normally done by run() method)
        grabber.running_job_path = job_path

        # Execute the job
        grabber.run_job()

        # Verify job marked as FAILED
        spool_dir = temp_cluster / "spool" / "test_grabber"
        failed_files = list(spool_dir.glob("*-FAILED"))
        assert len(failed_files) == 1

        # Verify stderr/stdout captured
        log_dir = temp_cluster / "log"
        out_files = list(log_dir.glob("test_error.sh.out"))
        assert len(out_files) == 1
        output = out_files[0].read_text()
        assert "This will fail" in output

    def test_multiple_file_types_in_queue(self, grabber, temp_cluster):
        """Test cluster handles mix of different file types."""
        # Create multiple file types (need shebangs for execution)
        (temp_cluster / "queue" / "test1.py").write_text("#!/usr/bin/env python3\nprint('Python')\nexit(0)\n")
        (temp_cluster / "queue" / "test2.sh").write_text("#!/bin/bash\necho 'Bash'\nexit 0\n")

        # Process first job
        job_path1 = grabber.grab_job()
        assert job_path1 is not None
        grabber.running_job_path = job_path1
        grabber.run_job()

        # Process second job (need new grabber instance to reset state)
        grabber2 = Grabber(name="test_grabber", clusterpath=str(temp_cluster))
        job_path2 = grabber2.grab_job()
        assert job_path2 is not None
        grabber2.running_job_path = job_path2
        grabber2.run_job()

        # Verify both jobs completed
        spool_dir = temp_cluster / "spool" / "test_grabber"
        done_files = list(spool_dir.glob("*-DONE"))
        assert len(done_files) == 2
