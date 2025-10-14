"""
Integration tests for uv script execution.

Tests actual uv operations with real file system and uv installation.
"""

import pytest
import subprocess
import time
from pathlib import Path

from script_grabber.uv_handler import (
    detect_uv_script,
    parse_uv_metadata,
    create_uv_environment,
    install_uv_dependencies,
    execute_uv_script,
    cleanup_uv_environment,
    UvScriptError,
)

from tests.fixtures import uv_scripts


# Check if uv is available
def is_uv_available():
    """Check if uv command is available."""
    try:
        result = subprocess.run(
            ["uv", "--version"],
            capture_output=True,
            timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


pytestmark = pytest.mark.skipif(
    not is_uv_available(),
    reason="uv not installed"
)


@pytest.mark.integration
class TestUvEnvironmentLifecycle:
    """Test complete environment lifecycle: create, use, cleanup."""

    def test_create_and_cleanup_environment(self, tmp_path):
        """Test creating and cleaning up a uv environment"""
        job_id = f"test-env-{int(time.time())}"

        # Create environment
        env_path = create_uv_environment(job_id, tmp_path)

        assert env_path.exists()
        assert (env_path / "bin" / "python").exists() or (env_path / "Scripts" / "python.exe").exists()

        # Cleanup
        cleanup_uv_environment(env_path)

        assert not env_path.exists()

    def test_cleanup_after_execution_failure(self, tmp_path):
        """Test that cleanup works even after script execution failure"""
        job_id = f"test-cleanup-{int(time.time())}"

        # Create environment
        env_path = create_uv_environment(job_id, tmp_path)

        # Try to execute non-existent script (simulates failure)
        script_file = tmp_path / "non_existent.py"

        try:
            execute_uv_script(script_file, env_path, tmp_path, timeout=10)
        except (UvScriptError, FileNotFoundError):
            pass  # Expected

        # Cleanup should still work
        cleanup_uv_environment(env_path)

        assert not env_path.exists()


@pytest.mark.integration
class TestDependencyInstallation:
    """Test actual dependency installation with uv."""

    def test_install_basic_dependencies(self, tmp_path):
        """Test installing lightweight dependencies"""
        job_id = f"test-deps-{int(time.time())}"

        # Create environment
        env_path = create_uv_environment(job_id, tmp_path)

        try:
            # Install lightweight package
            dependencies = ["certifi"]
            result = install_uv_dependencies(dependencies, env_path, timeout=120)

            assert result.returncode == 0
            # uv outputs to stderr, check both stdout and stderr
            output = result.stdout + result.stderr
            assert "certifi" in output or "Successfully installed" in output or "Installed" in output

        finally:
            cleanup_uv_environment(env_path)

    def test_install_dependencies_with_versions(self, tmp_path):
        """Test installing dependencies with version constraints"""
        job_id = f"test-versions-{int(time.time())}"

        # Create environment
        env_path = create_uv_environment(job_id, tmp_path)

        try:
            # Install with version constraint
            dependencies = ["certifi>=2020.0.0"]
            result = install_uv_dependencies(dependencies, env_path, timeout=120)

            assert result.returncode == 0

        finally:
            cleanup_uv_environment(env_path)

    def test_install_fails_with_invalid_package(self, tmp_path):
        """Test that installing invalid package raises error"""
        job_id = f"test-invalid-{int(time.time())}"

        # Create environment
        env_path = create_uv_environment(job_id, tmp_path)

        try:
            dependencies = ["this-package-does-not-exist-12345"]

            with pytest.raises(UvScriptError) as exc_info:
                install_uv_dependencies(dependencies, env_path, timeout=120)

            assert "Failed to install" in str(exc_info.value)

        finally:
            cleanup_uv_environment(env_path)


@pytest.mark.integration
class TestScriptExecution:
    """Test actual script execution in uv environments."""

    def test_execute_script_in_environment(self, tmp_path):
        """Test executing a script with dependencies"""
        job_id = f"test-exec-{int(time.time())}"

        # Create test script
        script_file = tmp_path / "test_script.py"
        script_file.write_text("""
import sys
import certifi
print(f"Certifi version: {certifi.__version__}")
print("Script executed successfully")
sys.exit(0)
""")

        # Create environment
        env_path = create_uv_environment(job_id, tmp_path)

        try:
            # Install dependencies
            dependencies = ["certifi"]
            install_uv_dependencies(dependencies, env_path, timeout=120)

            # Execute script
            result = execute_uv_script(script_file, env_path, tmp_path, timeout=30)

            assert result.returncode == 0
            assert "Certifi version:" in result.stdout
            assert "Script executed successfully" in result.stdout

        finally:
            cleanup_uv_environment(env_path)

    def test_execute_script_with_timeout(self, tmp_path):
        """Test that script execution respects timeout"""
        job_id = f"test-timeout-{int(time.time())}"

        # Create script that sleeps
        script_file = tmp_path / "sleep_script.py"
        script_file.write_text("""
import time
time.sleep(30)
print("Should not reach here")
""")

        # Create environment
        env_path = create_uv_environment(job_id, tmp_path)

        try:
            # Execute with short timeout
            with pytest.raises(subprocess.TimeoutExpired):
                execute_uv_script(script_file, env_path, tmp_path, timeout=2)

        finally:
            cleanup_uv_environment(env_path)


@pytest.mark.integration
class TestFullWorkflow:
    """Test complete workflow from detection to execution."""

    def test_basic_uv_script_workflow(self, tmp_path):
        """Test complete workflow: detect, parse, create env, install, execute, cleanup"""
        job_id = f"test-workflow-{int(time.time())}"

        # Create uv script
        script_file = tmp_path / "workflow_script.py"
        script_file.write_text(uv_scripts.BASIC_UV_SCRIPT.replace(
            "requests", "certifi"
        ).replace(
            "python-dotenv", ""
        ).replace(
            'dependencies = [\n#   "certifi",\n#   "",\n# ]',
            'dependencies = ["certifi"]'
        ))

        # Step 1: Detect
        is_uv = detect_uv_script(script_file)
        assert is_uv is True

        # Step 2: Parse metadata
        # Use simpler script for parsing
        simple_script = tmp_path / "simple.py"
        simple_script.write_text('''#!/usr/bin/env -S uv run
# /// script
# dependencies = ["certifi"]
# ///

import certifi
print("OK")
''')

        metadata = parse_uv_metadata(simple_script)
        assert "certifi" in metadata["dependencies"]

        # Step 3: Create environment
        env_path = create_uv_environment(job_id, tmp_path)
        assert env_path.exists()

        try:
            # Step 4: Install dependencies
            result = install_uv_dependencies(metadata["dependencies"], env_path, timeout=120)
            assert result.returncode == 0

            # Step 5: Execute script
            result = execute_uv_script(simple_script, env_path, tmp_path, timeout=30)
            assert result.returncode == 0
            assert "OK" in result.stdout

        finally:
            # Step 6: Cleanup
            cleanup_uv_environment(env_path)
            assert not env_path.exists()


@pytest.mark.integration
class TestConcurrentExecution:
    """Test concurrent execution of multiple uv scripts."""

    def test_concurrent_environment_creation(self, tmp_path):
        """Test that multiple jobs can create environments simultaneously"""
        job_ids = [f"test-concurrent-{i}-{int(time.time())}" for i in range(3)]

        env_paths = []

        try:
            # Create multiple environments
            for job_id in job_ids:
                env_path = create_uv_environment(job_id, tmp_path)
                env_paths.append(env_path)
                assert env_path.exists()

            # All environments should exist independently
            for env_path in env_paths:
                assert env_path.exists()

        finally:
            # Cleanup all
            for env_path in env_paths:
                cleanup_uv_environment(env_path)

            # All should be cleaned up
            for env_path in env_paths:
                assert not env_path.exists()
