"""Unit tests for file type detection in Grabber."""

import pytest
from pathlib import Path
import tempfile
import os
from script_grabber.grabber import Grabber


@pytest.fixture
def temp_cluster():
    """Create a temporary cluster directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def grabber(temp_cluster):
    """Create a Grabber instance for testing."""
    return Grabber(name="test_grabber", clusterpath=str(temp_cluster))


class TestFileTypeDetection:
    """Test file type detection logic."""

    def test_detect_shebang_bash(self, grabber, temp_cluster):
        """Test detection of bash shebang."""
        test_file = temp_cluster / "test.sh"
        test_file.write_text("#!/bin/bash\necho 'test'\n")

        command, description = grabber.detect_execution_method(test_file)

        assert command == ["/bin/bash", str(test_file)]
        assert "shebang" in description
        assert "/bin/bash" in description

    def test_detect_shebang_env_python(self, grabber, temp_cluster):
        """Test detection of env-based Python shebang."""
        test_file = temp_cluster / "test.py"
        test_file.write_text("#!/usr/bin/env python3\nprint('test')\n")

        command, description = grabber.detect_execution_method(test_file)

        assert command == ["python3", str(test_file)]
        assert "shebang env" in description
        assert "python3" in description

    def test_detect_shebang_env_node(self, grabber, temp_cluster):
        """Test detection of env-based Node.js shebang."""
        test_file = temp_cluster / "test.js"
        test_file.write_text("#!/usr/bin/env node\nconsole.log('test');\n")

        command, description = grabber.detect_execution_method(test_file)

        assert command == ["node", str(test_file)]
        assert "shebang env" in description
        assert "node" in description

    def test_detect_extension_python(self, grabber, temp_cluster):
        """Test detection of Python by .py extension."""
        test_file = temp_cluster / "test.py"
        test_file.write_text("print('test')\n")  # No shebang

        command, description = grabber.detect_execution_method(test_file)

        assert command == ["python3", str(test_file)]
        assert "extension .py" in description
        assert "Python interpreter" in description

    def test_detect_extension_shell(self, grabber, temp_cluster):
        """Test detection of shell by .sh extension."""
        test_file = temp_cluster / "test.sh"
        test_file.write_text("echo 'test'\n")  # No shebang

        command, description = grabber.detect_execution_method(test_file)

        assert command == ["/bin/bash", str(test_file)]
        assert "extension .sh" in description
        assert "Bash shell" in description

    def test_detect_extension_javascript(self, grabber, temp_cluster):
        """Test detection of Node.js by .js extension."""
        test_file = temp_cluster / "test.js"
        test_file.write_text("console.log('test');\n")  # No shebang

        command, description = grabber.detect_execution_method(test_file)

        assert command == ["node", str(test_file)]
        assert "extension .js" in description
        assert "Node.js" in description

    def test_detect_extension_ruby(self, grabber, temp_cluster):
        """Test detection of Ruby by .rb extension."""
        test_file = temp_cluster / "test.rb"
        test_file.write_text("puts 'test'\n")  # No shebang

        command, description = grabber.detect_execution_method(test_file)

        assert command == ["ruby", str(test_file)]
        assert "extension .rb" in description
        assert "Ruby" in description

    def test_detect_no_extension(self, grabber, temp_cluster):
        """Test handling of files without extension (binary)."""
        test_file = temp_cluster / "testfile"
        test_file.write_text("echo 'test'\n")  # No shebang, no extension

        command, description = grabber.detect_execution_method(test_file)

        assert command == [str(test_file)]
        assert "direct execution" in description

    def test_detect_unknown_extension(self, grabber, temp_cluster):
        """Test handling of unknown extensions (fallback to direct execution)."""
        test_file = temp_cluster / "test.xyz"
        test_file.write_text("echo 'test'\n")  # No shebang, unknown extension

        command, description = grabber.detect_execution_method(test_file)

        assert command == [str(test_file)]
        assert "direct execution" in description

    def test_shebang_with_args(self, grabber, temp_cluster):
        """Test shebang with additional arguments."""
        test_file = temp_cluster / "test.py"
        test_file.write_text("#!/usr/bin/python3 -u\nprint('test')\n")

        command, description = grabber.detect_execution_method(test_file)

        # Should extract just the interpreter path
        assert command[0] == "/usr/bin/python3"
        assert command[1] == str(test_file)
        assert "shebang" in description

    def test_shebang_read_error_fallback(self, grabber, temp_cluster):
        """Test fallback to extension when shebang read fails."""
        test_file = temp_cluster / "test.py"
        test_file.write_text("print('test')\n")

        # Make file unreadable
        os.chmod(test_file, 0o000)

        try:
            command, description = grabber.detect_execution_method(test_file)
            # Should fall back to extension-based detection
            assert "extension .py" in description or "direct execution" in description
        finally:
            # Restore permissions for cleanup
            os.chmod(test_file, 0o644)

    def test_binary_file(self, grabber, temp_cluster):
        """Test handling of binary files."""
        test_file = temp_cluster / "testbin"
        # Write some binary data
        test_file.write_bytes(b'\x7fELF\x00\x00\x00\x00')

        command, description = grabber.detect_execution_method(test_file)

        assert command == [str(test_file)]
        assert "direct execution" in description

    def test_shebang_priority_over_extension(self, grabber, temp_cluster):
        """Test that shebang takes priority over extension."""
        test_file = temp_cluster / "test.sh"
        # Has .sh extension but Python shebang
        test_file.write_text("#!/usr/bin/env python3\nprint('test')\n")

        command, description = grabber.detect_execution_method(test_file)

        # Should use shebang (python3) not extension (bash)
        assert command == ["python3", str(test_file)]
        assert "shebang env" in description
        assert "python3" in description
