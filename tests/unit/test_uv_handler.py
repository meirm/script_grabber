"""
Unit tests for uv_handler module.

Tests detection, parsing, and core functionality in isolation with mocked dependencies.
"""

import pytest
import tempfile
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

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


class TestDetectUvScript:
    """Tests for detect_uv_script() function."""

    def test_detect_uv_script_with_standard_shebang(self, tmp_path):
        """Test detection of standard uv shebang: #!/usr/bin/env -S uv run"""
        script_file = tmp_path / "test_script.py"
        script_file.write_text(uv_scripts.BASIC_UV_SCRIPT)

        assert detect_uv_script(script_file) is True

    def test_detect_uv_script_with_alternative_shebang(self, tmp_path):
        """Test detection of alternative shebang: #!/usr/bin/env uv run"""
        script_file = tmp_path / "test_script.py"
        script_file.write_text(uv_scripts.ALT_SHEBANG_SCRIPT)

        assert detect_uv_script(script_file) is True

    def test_detect_returns_false_for_regular_python(self, tmp_path):
        """Test that regular Python scripts are not detected as uv scripts"""
        script_file = tmp_path / "regular.py"
        script_file.write_text(uv_scripts.REGULAR_PYTHON_SCRIPT)

        assert detect_uv_script(script_file) is False

    def test_detect_returns_false_for_bash(self, tmp_path):
        """Test that Bash scripts are not detected as uv scripts"""
        script_file = tmp_path / "script.sh"
        script_file.write_text(uv_scripts.BASH_SCRIPT)

        assert detect_uv_script(script_file) is False

    def test_detect_handles_file_not_found(self, tmp_path):
        """Test that FileNotFoundError is raised for non-existent files"""
        non_existent = tmp_path / "does_not_exist.py"

        with pytest.raises(FileNotFoundError):
            detect_uv_script(non_existent)

    def test_detect_handles_permission_error(self, tmp_path):
        """Test handling of permission errors"""
        script_file = tmp_path / "no_permission.py"
        script_file.write_text(uv_scripts.BASIC_UV_SCRIPT)
        script_file.chmod(0o000)  # Remove all permissions

        try:
            with pytest.raises(PermissionError):
                detect_uv_script(script_file)
        finally:
            script_file.chmod(0o644)  # Restore permissions for cleanup


class TestParseUvMetadata:
    """Tests for parse_uv_metadata() function."""

    def test_parse_basic_dependencies(self, tmp_path):
        """Test parsing basic dependency list"""
        script_file = tmp_path / "test_script.py"
        script_file.write_text(uv_scripts.BASIC_UV_SCRIPT)

        metadata = parse_uv_metadata(script_file)

        assert "dependencies" in metadata
        assert "requests" in metadata["dependencies"]
        assert "python-dotenv" in metadata["dependencies"]
        assert len(metadata["dependencies"]) == 2

    def test_parse_version_constraints(self, tmp_path):
        """Test parsing dependencies with version constraints"""
        script_file = tmp_path / "test_script.py"
        script_file.write_text(uv_scripts.VERSION_CONSTRAINTS_SCRIPT)

        metadata = parse_uv_metadata(script_file)

        assert "requests>=2.31.0" in metadata["dependencies"]
        assert "python-dotenv>=1.0.0,<2.0.0" in metadata["dependencies"]

    def test_parse_optional_dependencies(self, tmp_path):
        """Test parsing optional dependencies"""
        script_file = tmp_path / "test_script.py"
        script_file.write_text(uv_scripts.OPTIONAL_DEPS_SCRIPT)

        metadata = parse_uv_metadata(script_file)

        assert "optional_dependencies" in metadata
        # Optional dependencies format may vary

    def test_parse_empty_dependencies(self, tmp_path):
        """Test parsing script with empty dependencies list"""
        script_file = tmp_path / "test_script.py"
        script_file.write_text(uv_scripts.EMPTY_DEPS_SCRIPT)

        metadata = parse_uv_metadata(script_file)

        assert "dependencies" in metadata
        assert metadata["dependencies"] == []

    def test_parse_invalid_toml_raises_error(self, tmp_path):
        """Test that invalid TOML raises UvScriptError"""
        script_file = tmp_path / "invalid_toml.py"
        script_file.write_text(uv_scripts.INVALID_TOML_SCRIPT)

        with pytest.raises(UvScriptError) as exc_info:
            parse_uv_metadata(script_file)

        assert "Failed to parse" in str(exc_info.value)

    def test_parse_missing_end_marker_raises_error(self, tmp_path):
        """Test that missing end marker raises UvScriptError"""
        script_file = tmp_path / "missing_end.py"
        script_file.write_text(uv_scripts.MISSING_END_MARKER_SCRIPT)

        with pytest.raises(UvScriptError) as exc_info:
            parse_uv_metadata(script_file)

        assert "Unclosed" in str(exc_info.value) or "end marker" in str(exc_info.value)

    def test_parse_no_metadata_raises_error(self, tmp_path):
        """Test that scripts without metadata raise UvScriptError"""
        script_file = tmp_path / "no_metadata.py"
        script_file.write_text(uv_scripts.NO_METADATA_SCRIPT)

        with pytest.raises(UvScriptError) as exc_info:
            parse_uv_metadata(script_file)

        assert "No PEP 723 metadata block found" in str(exc_info.value)


class TestCreateUvEnvironment:
    """Tests for create_uv_environment() function."""

    @patch('subprocess.run')
    def test_create_environment_success(self, mock_run, tmp_path):
        """Test successful environment creation"""
        # Mock uv --version check
        mock_run.return_value = Mock(returncode=0, stdout="uv 0.1.0", stderr="")

        job_id = "test-job-123"
        env_path = tmp_path / "uv_envs" / job_id

        # Mock uv venv command and create the expected structure
        def run_side_effect(*args, **kwargs):
            if "venv" in args[0]:
                # Create the expected directory structure
                env_dir = Path(args[0][-1])
                env_dir.mkdir(parents=True, exist_ok=True)
                (env_dir / "bin").mkdir(exist_ok=True)
                (env_dir / "bin" / "python").touch()
                return Mock(returncode=0, stdout="Created environment", stderr="")
            return Mock(returncode=0, stdout="", stderr="")

        mock_run.side_effect = run_side_effect

        result = create_uv_environment(job_id, tmp_path)

        assert result == env_path
        assert result.exists()

    @patch('subprocess.run')
    def test_create_environment_uv_not_found(self, mock_run, tmp_path):
        """Test error when uv is not installed"""
        mock_run.side_effect = FileNotFoundError()

        with pytest.raises(UvScriptError) as exc_info:
            create_uv_environment("test-job", tmp_path)

        assert "uv not found" in str(exc_info.value)
        assert "Install uv" in str(exc_info.value)

    @patch('subprocess.run')
    def test_create_environment_command_fails(self, mock_run, tmp_path):
        """Test error when uv venv command fails"""
        # Mock successful version check
        version_check = Mock(returncode=0, stdout="uv 0.1.0")
        # Mock failed venv command
        venv_fail = Mock(returncode=1, stdout="", stderr="Error creating environment")

        mock_run.side_effect = [version_check, venv_fail]

        with pytest.raises(UvScriptError) as exc_info:
            create_uv_environment("test-job", tmp_path)

        assert "Failed to create uv environment" in str(exc_info.value)


class TestInstallUvDependencies:
    """Tests for install_uv_dependencies() function."""

    def test_install_empty_dependencies(self, tmp_path):
        """Test that empty dependency list is handled gracefully"""
        env_path = tmp_path / "env"
        result = install_uv_dependencies([], env_path)

        assert result.returncode == 0

    @patch('subprocess.run')
    def test_install_dependencies_success(self, mock_run, tmp_path):
        """Test successful dependency installation"""
        env_path = tmp_path / "env"
        (env_path / "bin").mkdir(parents=True)
        (env_path / "bin" / "python").touch()

        mock_run.return_value = Mock(
            returncode=0,
            stdout="Successfully installed requests",
            stderr=""
        )

        dependencies = ["requests", "python-dotenv"]
        result = install_uv_dependencies(dependencies, env_path)

        assert result.returncode == 0
        mock_run.assert_called_once()

    @patch('subprocess.run')
    def test_install_dependencies_failure(self, mock_run, tmp_path):
        """Test handling of installation failures"""
        env_path = tmp_path / "env"
        (env_path / "bin").mkdir(parents=True)
        (env_path / "bin" / "python").touch()

        mock_run.return_value = Mock(
            returncode=1,
            stdout="",
            stderr="Package not found"
        )

        dependencies = ["invalid-package-name"]

        with pytest.raises(UvScriptError) as exc_info:
            install_uv_dependencies(dependencies, env_path)

        assert "Failed to install dependencies" in str(exc_info.value)

    @patch('subprocess.run')
    def test_install_dependencies_timeout(self, mock_run, tmp_path):
        """Test handling of installation timeout"""
        env_path = tmp_path / "env"
        (env_path / "bin").mkdir(parents=True)
        (env_path / "bin" / "python").touch()

        mock_run.side_effect = subprocess.TimeoutExpired(cmd="uv pip install", timeout=10)

        dependencies = ["requests"]

        with pytest.raises(UvScriptError) as exc_info:
            install_uv_dependencies(dependencies, env_path, timeout=10)

        assert "timed out" in str(exc_info.value)


class TestExecuteUvScript:
    """Tests for execute_uv_script() function."""

    @patch('subprocess.run')
    def test_execute_script_success(self, mock_run, tmp_path):
        """Test successful script execution"""
        script_file = tmp_path / "script.py"
        script_file.write_text("print('Hello')")

        env_path = tmp_path / "env"
        (env_path / "bin").mkdir(parents=True)
        (env_path / "bin" / "python").touch()

        mock_run.return_value = Mock(
            returncode=0,
            stdout="Hello\n",
            stderr=""
        )

        result = execute_uv_script(script_file, env_path, tmp_path, timeout=60)

        assert result.returncode == 0
        assert "Hello" in result.stdout

    @patch('subprocess.run')
    def test_execute_script_timeout(self, mock_run, tmp_path):
        """Test script execution timeout"""
        script_file = tmp_path / "script.py"
        script_file.write_text("import time; time.sleep(100)")

        env_path = tmp_path / "env"
        (env_path / "bin").mkdir(parents=True)
        (env_path / "bin" / "python").touch()

        mock_run.side_effect = subprocess.TimeoutExpired(cmd="python", timeout=5)

        with pytest.raises(subprocess.TimeoutExpired):
            execute_uv_script(script_file, env_path, tmp_path, timeout=5)

    def test_execute_script_python_not_found(self, tmp_path):
        """Test error when Python executable not found in environment"""
        script_file = tmp_path / "script.py"
        script_file.write_text("print('Hello')")

        env_path = tmp_path / "env"
        # Don't create Python executable

        with pytest.raises(UvScriptError) as exc_info:
            execute_uv_script(script_file, env_path, tmp_path, timeout=60)

        assert "Python executable not found" in str(exc_info.value)


class TestCleanupUvEnvironment:
    """Tests for cleanup_uv_environment() function."""

    def test_cleanup_existing_environment(self, tmp_path):
        """Test cleanup of existing environment"""
        env_path = tmp_path / "env"
        env_path.mkdir()
        (env_path / "bin").mkdir()
        (env_path / "bin" / "python").touch()

        cleanup_uv_environment(env_path)

        assert not env_path.exists()

    def test_cleanup_non_existent_environment(self, tmp_path):
        """Test cleanup of non-existent environment (should not error)"""
        env_path = tmp_path / "non_existent"

        # Should not raise error
        cleanup_uv_environment(env_path)

    def test_cleanup_handles_permission_error(self, tmp_path):
        """Test that cleanup handles permission errors gracefully"""
        env_path = tmp_path / "env"
        env_path.mkdir()

        with patch('shutil.rmtree', side_effect=PermissionError("Permission denied")):
            # Should log warning but not raise
            cleanup_uv_environment(env_path)


@pytest.mark.unit
class TestUvScriptError:
    """Tests for UvScriptError exception."""

    def test_error_is_exception(self):
        """Test that UvScriptError is an Exception"""
        error = UvScriptError("test error")
        assert isinstance(error, Exception)

    def test_error_message(self):
        """Test error message handling"""
        message = "Test error message"
        error = UvScriptError(message)
        assert str(error) == message
