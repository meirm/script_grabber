"""
uv Single-File Script Handler

This module provides comprehensive support for executing Python scripts that use uv's
single-file dependency management feature (PEP 723). It handles detection, metadata parsing,
environment management, dependency installation, and script execution for uv scripts.

Key features:
- Detect uv scripts via shebang patterns
- Parse PEP 723 metadata blocks containing dependency specifications
- Create isolated temporary virtual environments
- Install dependencies using uv's fast dependency resolver
- Execute scripts within their dependency environment
- Clean up temporary environments after execution
- Handle errors gracefully with clear, actionable error messages

Example uv script format:
    #!/usr/bin/env -S uv run
    # /// script
    # dependencies = [
    #   "requests>=2.31.0",
    #   "python-dotenv",
    # ]
    # ///

    import requests
    print(f"Requests version: {requests.__version__}")

Author: ScriptGrabber Team
"""

import os
import sys
import shutil
import subprocess
import re
import logging
from pathlib import Path
from typing import Dict, List, Optional

# Handle tomllib import (built-in Python 3.11+) vs tomli (3.9-3.10)
try:
    import tomllib  # Python 3.11+
except ImportError:
    try:
        import tomli as tomllib  # Python 3.9-3.10
    except ImportError:
        tomllib = None  # Will raise error on usage


# Configure module logger
logger = logging.getLogger(__name__)


class UvScriptError(Exception):
    """Base exception for uv script handling errors."""
    pass


def detect_uv_script(file_path: Path) -> bool:
    """
    Detect if a script file is a uv single-file script by examining its shebang.

    Recognized shebang patterns:
    - #!/usr/bin/env -S uv run
    - #!/usr/bin/env uv run
    - #!/usr/bin/env uv

    Args:
        file_path: Path to the script file to examine

    Returns:
        True if the script has a uv shebang, False otherwise

    Raises:
        FileNotFoundError: If the file does not exist
        PermissionError: If the file cannot be read
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            first_line = f.readline().strip()

        # Match uv shebang patterns
        uv_patterns = [
            r'^#!\s*/usr/bin/env\s+-S\s+uv\s+run',  # #!/usr/bin/env -S uv run
            r'^#!\s*/usr/bin/env\s+uv\s+run',       # #!/usr/bin/env uv run
            r'^#!\s*/usr/bin/env\s+uv$',            # #!/usr/bin/env uv
        ]

        is_uv_script = any(re.match(pattern, first_line) for pattern in uv_patterns)

        if is_uv_script:
            logger.info(f"Detected uv script: {file_path}")
        else:
            logger.debug(f"Not a uv script: {file_path}")

        return is_uv_script

    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        raise
    except PermissionError:
        logger.error(f"Permission denied reading file: {file_path}")
        raise
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {e}")
        return False


def parse_uv_metadata(file_path: Path) -> Dict[str, List[str]]:
    """
    Parse PEP 723 metadata block from a uv script file.

    Extracts the TOML metadata block marked by:
        # /// script
        # ... TOML content ...
        # ///

    Args:
        file_path: Path to the uv script file

    Returns:
        Dictionary containing parsed metadata with keys:
        - "dependencies": List of dependency specifications
        - "optional_dependencies": Dict of optional dependency groups (if present)

    Raises:
        UvScriptError: If metadata block is missing, malformed, or invalid TOML
        FileNotFoundError: If the file does not exist
    """
    if tomllib is None:
        raise UvScriptError(
            "TOML parsing library not available. "
            "Install tomli for Python <3.11: pip install tomli"
        )

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # Find metadata block markers
        start_marker = "# /// script"
        end_marker = "# ///"

        start_idx = None
        end_idx = None

        for i, line in enumerate(lines):
            line_stripped = line.strip()
            if line_stripped == start_marker:
                start_idx = i
            elif line_stripped == end_marker and start_idx is not None:
                end_idx = i
                break

        if start_idx is None:
            raise UvScriptError(
                f"No PEP 723 metadata block found in {file_path}. "
                f"Expected '# /// script' marker at the beginning of the script."
            )

        if end_idx is None:
            raise UvScriptError(
                f"Unclosed PEP 723 metadata block in {file_path}. "
                f"Expected '# ///' end marker."
            )

        # Extract TOML content (remove leading '# ' from each line)
        toml_lines = []
        for line in lines[start_idx + 1:end_idx]:
            # Remove leading '# ' or '#' from comment lines
            stripped = line.strip()
            if stripped.startswith('# '):
                toml_lines.append(stripped[2:])
            elif stripped.startswith('#'):
                toml_lines.append(stripped[1:])
            else:
                toml_lines.append(stripped)

        toml_content = '\n'.join(toml_lines)

        if not toml_content.strip():
            raise UvScriptError(
                f"Empty PEP 723 metadata block in {file_path}. "
                f"At least 'dependencies' field is required."
            )

        # Parse TOML
        try:
            metadata = tomllib.loads(toml_content)
        except Exception as e:
            raise UvScriptError(
                f"Failed to parse PEP 723 metadata in {file_path}: {e}\n"
                f"Metadata content:\n{toml_content}"
            )

        # Extract dependencies
        dependencies = metadata.get("dependencies", [])
        optional_dependencies = metadata.get("optional-dependencies", {})

        if not isinstance(dependencies, list):
            raise UvScriptError(
                f"Invalid 'dependencies' field in {file_path}. "
                f"Expected a list, got {type(dependencies).__name__}"
            )

        logger.info(
            f"Parsed metadata from {file_path}: "
            f"{len(dependencies)} dependencies, "
            f"{len(optional_dependencies)} optional dependency groups"
        )

        return {
            "dependencies": dependencies,
            "optional_dependencies": optional_dependencies
        }

    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        raise
    except UvScriptError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error parsing metadata from {file_path}: {e}")
        raise UvScriptError(f"Failed to parse metadata: {e}")


def create_uv_environment(job_id: str, temp_path: Path) -> Path:
    """
    Create an isolated temporary virtual environment for a uv script.

    Creates a directory structure: <temp_path>/uv_envs/<job_id>/
    and initializes a uv virtual environment within it.

    Args:
        job_id: Unique identifier for the job (used in directory name)
        temp_path: Base path for temporary files (typically <clusterpath>/temp)

    Returns:
        Path to the created environment directory

    Raises:
        UvScriptError: If uv is not available or environment creation fails
    """
    # Check if uv is available
    try:
        result = subprocess.run(
            ["uv", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode != 0:
            raise UvScriptError(
                "uv command failed. Install uv: "
                "curl -LsSf https://astral.sh/uv/install.sh | sh"
            )
    except FileNotFoundError:
        raise UvScriptError(
            "uv not found. Install uv: "
            "curl -LsSf https://astral.sh/uv/install.sh | sh"
        )
    except subprocess.TimeoutExpired:
        raise UvScriptError("uv command timed out checking version")

    # Create environment directory
    env_base = temp_path / "uv_envs"
    env_base.mkdir(parents=True, exist_ok=True)

    env_path = env_base / job_id

    if env_path.exists():
        logger.warning(f"Environment directory already exists: {env_path}. Removing it.")
        shutil.rmtree(env_path, ignore_errors=True)

    logger.info(f"Creating uv environment: {env_path}")

    try:
        # Create virtual environment using uv
        result = subprocess.run(
            ["uv", "venv", str(env_path)],
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode != 0:
            raise UvScriptError(
                f"Failed to create uv environment:\n"
                f"stdout: {result.stdout}\n"
                f"stderr: {result.stderr}"
            )

        # Validate environment creation
        python_exe = env_path / "bin" / "python"
        if os.name == "nt":  # Windows
            python_exe = env_path / "Scripts" / "python.exe"

        if not python_exe.exists():
            raise UvScriptError(
                f"Environment created but Python executable not found: {python_exe}"
            )

        logger.info(f"Successfully created uv environment: {env_path}")
        logger.debug(f"uv venv output:\n{result.stdout}")

        return env_path

    except subprocess.TimeoutExpired:
        raise UvScriptError("uv venv command timed out (>60s)")
    except UvScriptError:
        raise
    except Exception as e:
        raise UvScriptError(f"Unexpected error creating environment: {e}")


def install_uv_dependencies(
    dependencies: List[str],
    env_path: Path,
    timeout: int = 300
) -> subprocess.CompletedProcess:
    """
    Install dependencies into a uv virtual environment.

    Uses uv's fast dependency resolver to install packages from PyPI.

    Args:
        dependencies: List of package specifications (e.g., ["requests>=2.31.0", "pandas"])
        env_path: Path to the uv environment
        timeout: Maximum time in seconds for installation (default 300 = 5 minutes)

    Returns:
        subprocess.CompletedProcess with installation results

    Raises:
        UvScriptError: If installation fails
    """
    if not dependencies:
        logger.info("No dependencies to install")
        return subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr=""
        )

    # Determine Python executable path
    python_exe = env_path / "bin" / "python"
    if os.name == "nt":  # Windows
        python_exe = env_path / "Scripts" / "python.exe"

    if not python_exe.exists():
        raise UvScriptError(f"Python executable not found in environment: {python_exe}")

    logger.info(f"Installing {len(dependencies)} dependencies: {dependencies}")

    try:
        # Install dependencies using uv pip install
        cmd = ["uv", "pip", "install", "--python", str(python_exe)] + dependencies

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )

        if result.returncode != 0:
            raise UvScriptError(
                f"Failed to install dependencies: {dependencies}\n"
                f"Command: {' '.join(cmd)}\n"
                f"stdout: {result.stdout}\n"
                f"stderr: {result.stderr}"
            )

        logger.info(f"Successfully installed dependencies")
        logger.debug(f"Installation output:\n{result.stdout}")

        return result

    except subprocess.TimeoutExpired:
        raise UvScriptError(
            f"Dependency installation timed out (>{timeout}s). "
            f"Consider increasing timeout for large dependency trees."
        )
    except UvScriptError:
        raise
    except Exception as e:
        raise UvScriptError(f"Unexpected error installing dependencies: {e}")


def execute_uv_script(
    script_path: Path,
    env_path: Path,
    cwd: Path,
    timeout: int
) -> subprocess.CompletedProcess:
    """
    Execute a uv script within its isolated environment.

    Args:
        script_path: Path to the script file to execute
        env_path: Path to the uv environment containing dependencies
        cwd: Working directory for script execution
        timeout: Maximum execution time in seconds

    Returns:
        subprocess.CompletedProcess with script execution results

    Raises:
        UvScriptError: If script execution setup fails
        subprocess.TimeoutExpired: If script execution exceeds timeout
    """
    # Determine Python executable path
    python_exe = env_path / "bin" / "python"
    if os.name == "nt":  # Windows
        python_exe = env_path / "Scripts" / "python.exe"

    if not python_exe.exists():
        raise UvScriptError(f"Python executable not found in environment: {python_exe}")

    if not script_path.exists():
        raise UvScriptError(f"Script file not found: {script_path}")

    logger.info(f"Executing uv script: {script_path}")
    logger.debug(f"Using Python: {python_exe}")
    logger.debug(f"Working directory: {cwd}")
    logger.debug(f"Timeout: {timeout}s")

    try:
        cmd = [str(python_exe), str(script_path)]

        result = subprocess.run(
            cmd,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout
        )

        logger.info(
            f"Script execution completed: exit code {result.returncode}"
        )
        logger.debug(f"Script stdout:\n{result.stdout}")
        if result.stderr:
            logger.debug(f"Script stderr:\n{result.stderr}")

        return result

    except subprocess.TimeoutExpired as e:
        logger.warning(f"Script execution timed out after {timeout}s")
        raise
    except Exception as e:
        raise UvScriptError(f"Unexpected error executing script: {e}")


def cleanup_uv_environment(env_path: Path) -> None:
    """
    Clean up a temporary uv environment.

    Removes the environment directory and all its contents. Failures are logged
    but do not raise exceptions (cleanup is best-effort).

    Args:
        env_path: Path to the environment directory to remove
    """
    if not env_path.exists():
        logger.debug(f"Environment already removed or doesn't exist: {env_path}")
        return

    logger.info(f"Cleaning up uv environment: {env_path}")

    try:
        shutil.rmtree(env_path)
        logger.info(f"Successfully cleaned up environment: {env_path}")
    except Exception as e:
        logger.warning(
            f"Failed to clean up environment {env_path}: {e}. "
            f"Manual cleanup may be required."
        )
