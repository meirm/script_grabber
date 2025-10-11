# Chore: Migrate to uv for Build, Dependency Management, and Testing

## Chore Description
Migrate the script_grabber project from Poetry and pip to uv as the primary tool for:
- Building the project distribution packages
- Installing and managing dependencies
- Running tests and development workflows

This migration will modernize the project's tooling, improve build performance, and provide better dependency resolution. The project currently uses Poetry for build configuration (pyproject.toml) and pip for dependency installation. We'll transition to uv while maintaining compatibility with the existing project structure.

## Relevant Files
Use these files to resolve the chore:

- `pyproject.toml` - Contains Poetry build configuration, dependencies, and CLI entry points. Need to ensure it remains compatible with uv's build backend while updating build system requirements.
- `requirements.txt` - Currently only contains "poetry" as a dependency. Will be replaced with proper dependency list or removed in favor of pyproject.toml-only dependency management.
- `README.md` - Contains installation and usage instructions that reference Poetry and pip. Must be updated to reflect uv commands.
- `Dockerfile` - Uses pip to install the package. Must be updated to use uv for package installation.
- `docker-compose.yaml` - No direct changes needed, but should be tested to ensure container builds work with updated Dockerfile.
- `CLAUDE.md` - Contains developer guidance that references Poetry and pip commands. Must be updated to reflect uv workflow.

### New Files
- `.python-version` - Optional file to pin Python version for uv to use consistently across environments.

## Step by Step Tasks

### 1. Install uv locally for development
- Ensure uv is available on the development machine
- Verify uv installation with `uv --version`
- Document uv installation in README.md

### 2. Update pyproject.toml for uv compatibility
- Keep the existing Poetry metadata (name, version, description, authors, etc.) as it's compatible with uv
- Update `[build-system]` section to use a standard PEP 517 backend that uv supports (setuptools or hatchling)
- Ensure `[tool.poetry.scripts]` entry points are compatible with standard setuptools entry points
- Move dependencies from Poetry format to standard PEP 621 format in `[project]` section
- Keep pytest as a dev dependency

### 3. Remove/Update requirements.txt
- Since uv reads dependencies from pyproject.toml, evaluate if requirements.txt is still needed
- Either remove requirements.txt entirely or generate it from pyproject.toml using `uv pip compile pyproject.toml`
- Update .gitignore if removing requirements.txt

### 4. Update README.md installation instructions
- Replace `pip install -r requirements.txt` with uv equivalent
- Replace `poetry build` and `poetry install` with uv commands
- Update development setup instructions to use uv
- Add uv installation instructions as a prerequisite
- Update command examples to use `uv run` where appropriate

### 5. Update CLAUDE.md developer guidance
- Replace Poetry and pip commands with uv equivalents in all examples
- Update "Setup and Installation" section with uv commands
- Update "Running Grabbers" section to show uv run examples
- Update "Testing Jobs" section if test infrastructure changes
- Ensure all code examples reflect the new uv workflow

### 6. Update Dockerfile for uv
- Replace `pip install --upgrade pip` with uv installation
- Replace `pip install --no-cache-dir script_grabber` with uv package installation
- Consider using official uv base images or installing uv in the container
- Optimize Docker layer caching for uv dependencies

### 7. Test the migration locally
- Clean existing Poetry artifacts (`rm -rf dist/ *.egg-info .venv`)
- Build the project using uv: `uv build`
- Install the project in development mode: `uv pip install -e .`
- Verify CLI entry point works: `grabber --help` or test execution
- Verify the package can be installed from the built wheel

### 8. Update CI/CD configurations (if any)
- Check for GitHub Actions, GitLab CI, or other CI configurations
- Update any CI scripts to use uv instead of Poetry/pip
- Ensure test commands use uv

### 9. Run Validation Commands
- Execute all validation commands listed below to ensure zero regressions
- Fix any issues that arise during validation
- Document any breaking changes or migration notes

## Validation Commands
Execute every command to validate the chore is complete with zero regressions.

- `uv --version` - Verify uv is installed and accessible
- `uv build` - Build the project and verify it produces valid distribution packages (wheel and sdist)
- `uv pip install -e .` - Install the package in editable mode and verify no errors
- `grabber --help` - Verify CLI entry point is properly registered and accessible
- `uv run pytest -v` - Run tests if any exist (create basic smoke tests if none exist)
- `python -m script_grabber.grabber --help` - Verify module can be imported and executed directly
- `docker build -t script_grabber:test .` - Verify Docker build works with updated Dockerfile
- `uv pip list` - Verify installed packages and dependencies are correct

## Notes
- **uv** is a modern Python package manager and build tool written in Rust, offering significant performance improvements over pip and Poetry
- The project uses Poetry's build backend currently (`poetry.core.masonry.api`), which needs to be replaced with a standard PEP 517 backend like `setuptools.build_meta` or `hatchling.build`
- The CLI entry point `grabber = "script_grabber.grabber:main"` should work with standard setuptools without modification
- uv can directly install from pyproject.toml without needing a separate requirements.txt file
- Consider adding `uv.lock` to version control for reproducible builds (similar to poetry.lock)
- The project has minimal dependencies (just pytest for development), making the migration straightforward
- Ensure backwards compatibility: users should still be able to install via `pip install script-grabber` from PyPI
- Test the Docker container after migration to ensure it builds and runs correctly with uv
